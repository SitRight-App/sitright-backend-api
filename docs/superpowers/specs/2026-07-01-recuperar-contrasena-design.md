# Recuperar contraseña de punta a punta (front + back)

Fecha: 2026-07-01
Repos: `sitright-backend-api` (contexto `iam`) + `sitright-web-client` (feature `iam`)
HU: HU-27 (recuperación de contraseña)

## 1. Contexto y problema

El flujo de recuperación está a medias: el frontend tiene la pantalla "Olvidé mi
contraseña" (`/forgot-password`) que llama `POST /auth/forgot-password`, pero el
backend responde `202` uniforme y **no genera token ni envía correo** — el handler
`handle_request_password_reset` solo escribe un log (`"TTL 1h pendiente"`). No
existe el paso 2 (endpoint de confirmación ni pantalla para fijar la nueva
contraseña). Resultado: **nadie puede realmente restablecer su contraseña.**

Objetivo: completar el flujo de 2 pasos, funcional de punta a punta.

```
Paso 1  Pide el enlace   ->  POST /auth/forgot-password  ->  correo con enlace
Paso 2  Abre el enlace   ->  /reset-password?token=...   ->  POST /auth/reset-password
```

## 2. Decisiones tomadas

- **Modelo de token (enfoque A):** token opaco aleatorio; el **crudo** viaja en el
  enlace, en Mongo se guarda **solo su SHA-256**. Un solo uso, TTL 1h, se
  invalidan los previos del usuario al pedir uno nuevo. Si se filtra la BD, los
  tokens no sirven.
- **Proveedor de correo:** Brevo vía **SMTP** (`smtp-relay.brevo.com:587`,
  STARTTLS), usando `smtplib` en `asyncio.to_thread` (sin dependencia nueva).
- **URL del frontend:** `APP_BASE_URL`, default `https://sitright-web-client.netlify.app`.
- **Modo dev:** sin credenciales Brevo, no se envía y se **loguea el enlace**.

## 3. Fuera de alcance (YAGNI)

- Rate-limiting del `forgot-password`.
- Invalidar sesiones/JWT ya emitidos tras el reset (los JWT son stateless; se
  documenta como limitación conocida, no se resuelve aquí).
- Plantillas de correo elaboradas / branding HTML avanzado (basta texto + HTML simple).

## 4. Backend — `sitright-backend-api` (contexto `iam`)

Convención respetada: dominio y aplicación **no** importan `pymongo`/`smtplib`
(solo stdlib + dominio). Infraestructura implementa las interfaces del dominio.

### 4.1 Dominio

**Entidad** `domain/entities/password_reset_token.py`:

```python
@dataclass
class PasswordResetToken:
    id: UUID
    user_id: UUID
    token_hash: str            # sha256 hex del token crudo
    expires_at: datetime
    created_at: datetime
    used_at: datetime | None = None

    def is_valid(self, now: datetime) -> bool:
        return self.used_at is None and now < self.expires_at
```

**Repositorio** `domain/repositories/password_reset_token_repository.py` (Protocol):

```python
class PasswordResetTokenRepository(Protocol):
    async def save(self, token: PasswordResetToken) -> None: ...
    async def find_by_hash(self, token_hash: str) -> PasswordResetToken | None: ...
    async def invalidate_for_user(self, user_id: UUID) -> None: ...   # borra los previos
    async def mark_used(self, token_id: UUID, used_at: datetime) -> None: ...
```

**Servicio de email** `domain/services/email_service.py` (Protocol):

```python
class EmailService(Protocol):
    async def send_password_reset(
        self, to_email: str, to_name: str, reset_link: str
    ) -> None: ...
```

**Comando** `domain/model/commands/reset_password_command.py`:

```python
@dataclass
class ResetPasswordCommand:
    token: str
    new_password: str

class InvalidResetTokenError(Exception): ...
```

### 4.2 Aplicación — `UserCommandService`

Se agregan dependencias al `@dataclass`: `reset_token_repository`,
`email_service`, `app_base_url: str`, `reset_token_ttl_seconds: int`.
Generación e hasheo con stdlib (`secrets.token_urlsafe(32)`, `hashlib.sha256`).

`handle_request_password_reset` (reemplaza el stub):
1. Normaliza el correo, busca el usuario. Si no existe → `return` (respuesta
   uniforme AC2, sin enviar nada).
2. Si existe: `invalidate_for_user(user.id)`; genera `raw = secrets.token_urlsafe(32)`,
   `token_hash = sha256(raw)`; crea `PasswordResetToken(expires_at = now + ttl)`;
   `save`.
3. Arma `link = f"{app_base_url}/reset-password?token={raw}"`.
4. `await email_service.send_password_reset(user.email, user.name, link)`.
   Un error del email se loguea (`logger.warning`) y no se propaga.

`handle_reset_password(cmd)` (nuevo):
1. `if len(cmd.new_password) < 8: raise ValueError(...)`.
2. `token_hash = sha256(cmd.token)`; `t = await repo.find_by_hash(token_hash)`.
3. `if t is None or not t.is_valid(now): raise InvalidResetTokenError(...)`.
4. Carga el usuario `t.user_id`; si no existe o inactivo → `InvalidResetTokenError`.
5. `user.password_hash = password_service.hash(cmd.new_password)`;
   `user.updated_at = now`; `await user_repository.save(user)`.
6. `await repo.mark_used(t.id, now)` y `await repo.invalidate_for_user(user.id)`.

`IUserCommandService` (interfaz) suma `handle_reset_password`.

### 4.3 Interfaces REST

`interfaces/schemas/auth_schema.py`:

```python
class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)
```

`interfaces/rest/auth_router.py`:
- `POST /auth/reset-password`, `status_code=204`. Llama
  `service.handle_reset_password(ResetPasswordCommand(...))`.
- `InvalidResetTokenError` → `HTTPException(400, "El enlace no es válido o expiró")`
  (genérico, sin enumeración). `ValueError` (contraseña corta) → `400`.
- `/forgot-password` sin cambios de contrato (sigue `202` uniforme; ahora sí
  dispara correo cuando la cuenta existe).

### 4.4 Infraestructura

`infrastructure/persistence/mongo_password_reset_token_repository.py`:
- Colección `password_reset_tokens`. Índice único en `token_hash`. Índice TTL en
  `expires_at` (`expireAfterSeconds=0`) para que Mongo purgue los vencidos.
- Mapeo entidad<->documento con `_id = str(id)`, `user_id` str, fechas UTC.

`infrastructure/email/brevo_email_service.py` (implementa `EmailService`):
- Si `brevo_smtp_key` y `brevo_smtp_user` están vacíos → **modo dev**: no envía,
  `logger.info("[reset] enlace para %s: %s", to_email, reset_link)`.
- Si están configurados: construye un `EmailMessage` (texto + HTML con el enlace y
  el aviso de caducidad 1h) y lo envía con `smtplib.SMTP(host, port)` +
  `starttls()` + `login(user, key)`, todo dentro de `await asyncio.to_thread(...)`.
- Remitente: `email_sender_name <email_sender_address>`.

### 4.5 Config — `shared/config.py`

Nuevas variables (con defaults):

```python
app_base_url: str = "https://sitright-web-client.netlify.app"
reset_token_expires_seconds: int = 3600
brevo_smtp_host: str = "smtp-relay.brevo.com"
brevo_smtp_port: int = 587
brevo_smtp_user: str = ""          # SMTP login de Brevo
brevo_smtp_key: str = ""           # SMTP key de Brevo
email_sender_name: str = "SitRight"
email_sender_address: str = ""     # remitente verificado en Brevo
```

### 4.6 Wiring — `main.py`

En el arranque: construir `MongoPasswordResetTokenRepository(db)` y
`BrevoEmailService(settings)`; pasar ambos + `settings.app_base_url` y
`settings.reset_token_expires_seconds` al `UserCommandService`. Crear los índices
de la colección junto al resto de índices de arranque.

### 4.7 Tests (pytest)

Con fakes en memoria de `PasswordResetTokenRepository` y `EmailService`, y `now`
inyectable:
- `forgot`: correo existente → se guarda 1 token (hash, no crudo) y el email
  service recibió un `reset_link` con el token crudo; correo inexistente → 0 tokens,
  0 envíos; respuesta idéntica en ambos casos.
- `reset`: token válido → cambia `password_hash` (verificable con el password
  service) y marca el token usado; token vencido → `InvalidResetTokenError`;
  token ya usado → error (**un solo uso**); token inexistente → error;
  contraseña < 8 → `ValueError`.
- `invalidate_for_user`: pedir un segundo enlace invalida el primero.

## 5. Frontend — `sitright-web-client` (feature `iam`)

### 5.1 Servicio — `services/authService.ts`

```ts
export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await apiFetch<void>('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, new_password: newPassword }),
    skipAuth: true,
  })
}
```

### 5.2 `pages/ResetPasswordPage.tsx`

- Ruta `/reset-password`; lee `token` con `useSearchParams()`.
- Sin `token` → estado "Enlace inválido" con link a `/forgot-password`.
- Formulario: **nueva contraseña** + **confirmar**. Validación cliente: mín 8 y
  deben coincidir (mensajes claros antes de llamar al backend).
- Submit → `resetPassword(token, pass)`.
  - Éxito → `navigate('/login')` + toast de éxito ("Tu contraseña se actualizó,
    inicia sesión").
  - Error `400` → estado "El enlace no es válido o expiró" + link a
    `/forgot-password` para pedir uno nuevo.
- Reusa el layout de dos paneles (marca + formulario) de `ForgotPasswordPage`/login
  para coherencia visual.

### 5.3 Ruteo — `App.tsx`

```tsx
<Route path="/reset-password" element={<ResetPasswordPage />} />
```
(en el bloque de rutas públicas, junto a `/forgot-password`).

### 5.4 Tests

Componente (RTL + jsdom): sin token muestra el estado inválido; contraseñas que no
coinciden / cortas no llaman al servicio; éxito llama `resetPassword` y redirige;
error `400` muestra el estado de enlace vencido. Mock del servicio.

## 6. Setup manual (no bloquea el código)

En Brevo: verificar un remitente (un correo propio), obtener las credenciales
SMTP (login + key). Cargar en el entorno del backend (Render): `BREVO_SMTP_USER`,
`BREVO_SMTP_KEY`, `EMAIL_SENDER_ADDRESS`, y `APP_BASE_URL` si difiere del default.
Sin estas variables, el backend corre en modo dev (loguea el enlace).

## 7. Contrato entre repos (para planes separados)

- `POST /api/v1/auth/reset-password` — body `{ token: string, new_password: string }`
  → `204` OK | `400` enlace inválido/expirado o contraseña corta | `422` validación.
- El enlace del correo apunta a `{APP_BASE_URL}/reset-password?token=<crudo>`.

Cada repo se implementa con su propio plan; el backend primero (define y prueba el
endpoint), luego el frontend contra ese contrato.
