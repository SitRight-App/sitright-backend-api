# sitright-backend-api — CLAUDE.md

> API principal del sistema **SitRight**. FastAPI + Python 3.11 + MongoDB. 6 bounded contexts (sin ML, que vive en `sitright-ml-service`).

## Contexto completo

**Lee primero `sitright-workspace/CLAUDE.md`.** Este archivo solo contiene lo específico del backend principal.

Si estás trabajando en un monorepo local, el workspace está en `../sitright-workspace/`.

## Rol de este repo

- Recibe lecturas del ESP32 (de `sitright-firmware-vest`).
- Las persiste en MongoDB.
- Llama a `sitright-ml-service` para clasificar posturas.
- Expone la API REST que consume `sitright-web-client`.
- Maneja autenticación (JWT).

## Estructura

```
sitright-backend-api/
├── src/
│   ├── posture_capture/              # Bounded context 1
│   ├── posture_classification/       # Bounded context 2 (llama a ml-service)
│   ├── posture_visualization/        # Bounded context 3
│   ├── recommendations/              # Bounded context 4
│   ├── vest_management/              # Bounded context 5
│   ├── session_history/              # Bounded context 6
│   ├── iam/                          # Bounded context 7
│   ├── shared/                       # Value objects comunes, event bus
│   └── main.py                       # Entry point FastAPI
├── tests/                            # pytest, un subfolder por bounded context
├── requirements.txt
└── README.md
```

Cada bounded context sigue la estructura:

```
{contexto}/
├── domain/
│   ├── model/
│   │   ├── aggregates/          ← Aggregate root del contexto
│   │   ├── commands/            ← Objetos comando (dataclasses)
│   │   ├── queries/             ← Objetos consulta (dataclasses)
│   │   ├── entities/            ← Entidades del dominio
│   │   └── value_objects/       ← Value objects inmutables
│   ├── repositories/            ← Interfaces (Protocols) de repositorios
│   └── services/                ← Interfaces de servicios de dominio
├── application/
│   └── internal/
│       ├── command_services/    ← Implementaciones de comandos
│       ├── query_services/      ← Implementaciones de consultas
│       └── outbound_services/   ← Clientes externos (ej. ml-service)
├── infrastructure/
│   └── persistence/
│       └── repositories/        ← Implementaciones MongoDB de repositorios
└── interfaces/
    └── rest/
        ├── resources/           ← DTOs Pydantic (request / response)
        └── transform/           ← Assemblers (mapeo entre capas)
```

## Bounded contexts y HUs asociadas

| Contexto | HUs |
|---|---|
| posture_capture | HU-01, HU-02, HU-03 |
| posture_classification | HU-04, HU-05 |
| posture_visualization | HU-06, HU-07, HU-08, HU-09 |
| recommendations | HU-10, HU-11 |
| vest_management | HU-12, HU-13 |
| session_history | HU-14, HU-15, HU-16 |
| iam | HU-17, HU-18, HU-19, HU-20, HU-21 |

## Quick start

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Variables de entorno
export MONGO_URI="mongodb+srv://..."
export ML_SERVICE_URL="https://sitright-ml-service.onrender.com"
export JWT_SECRET="..."

# Arrancar
uvicorn src.main:app --reload --port 8000

# Healthcheck
curl http://localhost:8000/health

# Swagger
open http://localhost:8000/docs
```

## Convenciones

Ver `sitright-workspace/.claude/conventions.md § Python`.

**Reglas críticas:**

1. **Domain y Application NO importan FastAPI, pymongo, httpx.** Solo stdlib + typing + el propio dominio.
2. Infrastructure implementa las interfaces definidas en `domain/repositories/`.
3. Los routers en `interfaces/rest/` solo orquestan.
4. Queries no modifican estado. Commands no devuelven datos (salvo ID).
5. Nada de carpetas `utils/` genéricas.

## Contratos con otros servicios

- **sitright-firmware-vest → backend:** POST /api/v1/readings (JSON con 3 sensores).
- **backend → sitright-ml-service:** POST /ml/classify (ver `docs/api/ml-service-api.yaml` en el workspace).
- **sitright-web-client → backend:** ver `docs/api/backend-api.yaml` en el workspace.

## Autoría

**Claude no es autor ni co-autor de commits, PRs o issues.** Ver workspace para la regla completa.
