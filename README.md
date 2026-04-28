# sitright-backend-api

API principal del sistema **SitRight**. FastAPI + Python + MongoDB.

## Sobre el proyecto

Parte de la tesis **SitRight**: aplicación web con machine learning e IoT para mejorar la ergonomía postural en trabajadores sedentarios limeños mediante chaleco inteligente.

**Equipo:** Christopher Lecca, Mariano Ames (UPC — Ingeniería de Software).

## Arquitectura

Monolito modular con 7 bounded contexts (DDD ligero + CQRS):

- `posture_capture` — recepción y validación de datos IoT
- `posture_classification` — orquesta llamada al ml-service
- `posture_visualization` — dashboard tiempo real + alertas
- `recommendations` — recomendaciones ergonómicas
- `vest_management` — vinculación y calibración del chaleco
- `session_history` — historial y reportes
- `iam` — autenticación y gestión de usuarios

Ver `sitright-workspace/docs/decisions/ADR-003-monolito-modular-ddd.md` para el razonamiento.

## Stack

- Python 3.11
- FastAPI
- MongoDB (vía motor async)
- JWT para auth
- pytest para tests

## Relación con otros repos

- **sitright-firmware-vest** — envía datos a este backend.
- **sitright-ml-service** — este backend lo consulta para clasificar posturas.
- **sitright-web-client** — consume la API REST de este backend.
- **sitright-workspace** — documentación, ADRs y backlog (privado).

## Licencia

Proyecto académico — UPC 2026.
