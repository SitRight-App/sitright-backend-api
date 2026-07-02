import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .iam.application.internal.commandservices.user_command_service import (
    UserCommandService,
)
from .iam.application.internal.queryservices.user_query_service import UserQueryService
from .iam.application.seed_demo_users import seed_demo_users
from .iam.infrastructure.email.brevo_email_service import BrevoEmailService
from .iam.infrastructure.persistence.mongo_notification_repository import (
    MongoNotificationRepository,
)
from .iam.infrastructure.persistence.mongo_password_reset_token_repository import (
    MongoPasswordResetTokenRepository,
)
from .iam.infrastructure.persistence.mongo_user_repository import MongoUserRepository
from .iam.infrastructure.security.bcrypt_password_service import BcryptPasswordService
from .iam.infrastructure.security.jwt_token_service import JwtTokenService
from .iam.interfaces.rest import admin_router, auth_router, users_router
from .iam.interfaces.rest.dependencies import set_token_service
from .posture_capture.application.internal.commandservices.posture_capture_command_service import (
    PostureCaptureCommandService,
)
from .posture_capture.application.internal.queryservices.posture_capture_query_service import (
    PostureCaptureQueryService,
)
from .posture_capture.infrastructure.external.ml_client import MLServiceClient
from .posture_capture.infrastructure.persistence.mongo_posture_reading_repository import (
    MongoPostureReadingRepository,
)
from .posture_capture.interfaces.rest import readings_router
from .recommendations.application.internal.commandservices.recommendation_command_service import (
    RecommendationCommandService,
)
from .recommendations.application.internal.queryservices.recommendation_query_service import (
    RecommendationQueryService,
)
from .recommendations.infrastructure.persistence.mongo_applied_recommendation_repository import (
    MongoAppliedRecommendationRepository,
)
from .recommendations.interfaces.rest import recommendations_router as recommendations_router_mod
from .recommendations.interfaces.rest.recommendations_router import (
    router as recommendations_router,
)
from .session_history.application.internal.commandservices.session_command_service import (
    SessionCommandService,
)
from .session_history.application.internal.queryservices.session_query_service import (
    SessionQueryService,
)
from .session_history.infrastructure.external.last_sessions_adapter import (
    MongoLastSessionsAdapter,
)
from .session_history.infrastructure.external.readings_aggregator import (
    MongoReadingsAggregator,
)
from .session_history.infrastructure.external.session_stats_adapter import (
    MongoSessionStatsAdapter,
)
from .session_history.infrastructure.external.session_readings_reader import (
    MongoSessionReadingsReader,
)
from .session_history.infrastructure.external.zone_analyzer import (
    MongoZoneAnalyzer,
)
from .session_history.infrastructure.persistence.mongo_session_repository import (
    MongoPostureSessionRepository,
)
from .session_history.interfaces.rest import sessions_router
from .shared.adapters import (
    ActiveSessionLookupAdapter,
    SessionStarterAdapter,
    VestLookupAdapter,
)
from .shared.config import settings
from .shared.database import connect_database, disconnect_database, get_database
from .vest_management.application.internal.commandservices.vest_command_service import (
    VestCommandService,
)
from .vest_management.application.internal.queryservices.vest_query_service import (
    VestQueryService,
)
from .vest_management.infrastructure.external.linked_vests_adapter import (
    MongoLinkedVestsAdapter,
)
from .vest_management.infrastructure.persistence.mongo_vest_device_repository import (
    MongoVestDeviceRepository,
)
from .vest_management.interfaces.rest import vests_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_database()
    db = get_database()

    # ── IAM
    user_repo = MongoUserRepository(db)
    notif_repo = MongoNotificationRepository(db)
    password_service = BcryptPasswordService()
    token_service = JwtTokenService(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        access_expires_seconds=settings.jwt_access_expires_seconds,
        refresh_expires_seconds=settings.jwt_refresh_expires_seconds,
    )
    set_token_service(token_service)

    reset_token_repo = MongoPasswordResetTokenRepository(db)
    await reset_token_repo.ensure_indexes()
    email_service = BrevoEmailService(settings)

    user_command_service = UserCommandService(
        user_repository=user_repo,
        notification_repository=notif_repo,
        password_service=password_service,
        token_service=token_service,
        reset_token_repository=reset_token_repo,
        email_service=email_service,
        app_base_url=settings.app_base_url,
        reset_token_ttl_seconds=settings.reset_token_expires_seconds,
    )
    user_query_service = UserQueryService(
        user_repository=user_repo,
        notification_repository=notif_repo,
        session_stats=MongoSessionStatsAdapter(db),
    )
    auth_router.set_user_command_service(user_command_service)
    users_router.set_user_command_service(user_command_service)
    users_router.set_user_query_service(user_query_service)
    admin_router.set_user_command_service(user_command_service)
    admin_router.set_user_query_service(user_query_service)
    # HU-29 AC1 — adapters de "última sesión" y "chaleco vinculado" para
    # enriquecer la tabla del panel admin.
    admin_router.set_last_sessions_lookup(MongoLastSessionsAdapter(db))
    admin_router.set_linked_vests_lookup(MongoLinkedVestsAdapter(db))

    # Seed idempotente de cuentas demo (worker + admin) para la sustentación.
    await seed_demo_users(user_command_service)

    # ── Vest Management
    vest_repo = MongoVestDeviceRepository(db)
    vest_command_service = VestCommandService(
        vest_device_repository=vest_repo,
        password_service=password_service,
        expected_pairing_code=settings.vest_pairing_code or None,
    )
    vest_query_service = VestQueryService(vest_device_repository=vest_repo)
    vests_router.set_command_service(vest_command_service)
    vests_router.set_query_service(vest_query_service)

    # ── Posture Capture
    posture_repo = MongoPostureReadingRepository(db)
    ml_client = MLServiceClient(settings.ml_service_url)
    posture_capture_command_service = PostureCaptureCommandService(
        posture_reading_repository=posture_repo,
        ml_classifier=ml_client,
    )
    posture_capture_query_service = PostureCaptureQueryService(
        posture_reading_repository=posture_repo
    )
    readings_router.set_command_service(posture_capture_command_service)
    readings_router.set_query_service(posture_capture_query_service)
    # readings_router necesita resolver el chaleco del usuario para filtrar
    # /latest, /recent y /latest/raw, y validar 403 en POST por MAC (HU-02 AC3).
    readings_router.set_vest_query_service(vest_query_service)

    # ── Session History
    session_repo = MongoPostureSessionRepository(db)
    aggregator = MongoReadingsAggregator(db)
    session_command_service = SessionCommandService(
        session_repository=session_repo,
        readings_aggregator=aggregator,
    )
    session_query_service = SessionQueryService(
        session_repository=session_repo,
        zone_analyzer=MongoZoneAnalyzer(db),
        readings_reader=MongoSessionReadingsReader(db),
    )
    sessions_router.set_command_service(session_command_service)
    sessions_router.set_query_service(session_query_service)
    # El POST de lecturas (REST) asocia cada lectura a la sesión activa del
    # usuario, usando el query service de sesiones ya construido.
    readings_router.set_active_session_lookup(
        ActiveSessionLookupAdapter(session_query_service)
    )

    # ── Recommendations (catálogo estático + persistencia de 'aplicadas')
    applied_recs_repo = MongoAppliedRecommendationRepository(db)
    recommendations_router_mod.set_command_service(
        RecommendationCommandService(applied_repository=applied_recs_repo)
    )
    recommendations_router_mod.set_query_service(
        RecommendationQueryService(applied_repository=applied_recs_repo)
    )

    # ── MQTT (opcional, controlado por flag para que el dev local funcione sin broker)
    mqtt_subscriber = None
    if settings.mqtt_enabled and settings.mqtt_host:
        try:
            from .shared.mqtt import connect_mqtt
            from .vest_management.infrastructure.external.mqtt_vest_command_publisher import (
                MqttVestCommandPublisher,
            )
            from .posture_capture.interfaces.mqtt.posture_capture_subscriber import (
                PostureCaptureMqttSubscriber,
            )

            mqtt_client = await connect_mqtt()
            mqtt_publisher = MqttVestCommandPublisher(mqtt_client)
            # Inyectamos el publisher en el VestCommandService para que el
            # caso de uso send_vest_command pueda publicar al broker.
            vest_command_service.vest_command_publisher = mqtt_publisher

            mqtt_subscriber = PostureCaptureMqttSubscriber(
                mqtt_client=mqtt_client,
                command_service=posture_capture_command_service,
                vest_lookup=VestLookupAdapter(vest_repo),
                session_starter=SessionStarterAdapter(session_command_service),
            )
            await mqtt_subscriber.start()
        except Exception:
            logger.exception("Fallo iniciando MQTT, el sistema corre solo con REST")
            mqtt_subscriber = None

    yield

    if mqtt_subscriber is not None:
        await mqtt_subscriber.stop()
        try:
            from .shared.mqtt import disconnect_mqtt
            await disconnect_mqtt()
        except Exception:
            pass

    await disconnect_database()


OPENAPI_TAGS = [
    {
        "name": "iam",
        "description": "Identity & Access Management.",
    },
    {
        "name": "admin",
        "description": "Operaciones administrativas. Requiere rol `admin`.",
    },
    {
        "name": "posture_capture",
        "description": "Recepción de lecturas IMU del chaleco y consulta de las últimas/recientes.",
    },
    {
        "name": "vest_management",
        "description": "Ciclo de vida del chaleco: registro, vinculación, calibración, comandos.",
    },
    {
        "name": "session_history",
        "description": "Sesiones de uso y su resumen agregado.",
    },
    {
        "name": "recommendations",
        "description": "Catálogo de recomendaciones y marcado de aplicadas.",
    },
    {
        "name": "health",
        "description": "Liveness probe.",
    },
]


API_DESCRIPTION = """
**SitRight** — sistema de monitoreo postural en tiempo real para trabajadores
sedentarios mediante chaleco inteligente IoT.

## Cuentas demo

Sembradas idempotentemente al arrancar el servicio. Sirven para probar la
API sin necesidad de crear una cuenta nueva.

- **Trabajador**: `demo@sitright.app` / `Demo1234!`
- **Administrador**: `admin@sitright.app` / `Admin1234!`

## Autenticación

La mayoría de endpoints requiere `Authorization: Bearer <access_token>`.

1. Obtené el token con `POST /api/v1/auth/login`.
2. Click en el botón **Authorize** arriba a la derecha y pegá solo el
   `access_token` (Swagger agrega el prefijo `Bearer` automáticamente).
3. Si el token caduca, renovalo con `POST /api/v1/auth/refresh` usando
   el `refresh_token`.
"""


app = FastAPI(
    title="SitRight Backend API",
    description=API_DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
    swagger_ui_parameters={
        "defaultModelsExpandDepth": 0,
        "docExpansion": "list",
        "tagsSorter": "alpha",
        "operationsSorter": "alpha",
        "tryItOutEnabled": True,
        "persistAuthorization": True,
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(admin_router.router)
app.include_router(readings_router.router)
app.include_router(recommendations_router)
app.include_router(vests_router.router)
app.include_router(sessions_router.router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
