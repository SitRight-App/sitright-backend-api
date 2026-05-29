import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .iam.application.commands.login_handler import LoginHandler
from .iam.application.commands.mark_notification_read_handler import (
    MarkNotificationReadHandler,
)
from .iam.application.commands.refresh_token_handler import RefreshTokenHandler
from .iam.application.commands.register_user_handler import RegisterUserHandler
from .iam.application.commands.update_profile_handler import UpdateProfileHandler
from .iam.application.queries.count_unread_notifications_handler import (
    CountUnreadNotificationsHandler,
)
from .iam.application.queries.get_user_handler import GetUserHandler
from .iam.application.queries.list_notifications_handler import ListNotificationsHandler
from .iam.infrastructure.persistence.mongo_notification_repository import (
    MongoNotificationRepository,
)
from .iam.infrastructure.persistence.mongo_user_repository import MongoUserRepository
from .iam.infrastructure.security.bcrypt_password_service import BcryptPasswordService
from .iam.infrastructure.security.jwt_token_service import JwtTokenService
from .iam.interfaces.rest import auth_router, users_router
from .iam.interfaces.rest.dependencies import set_token_service
from .posture_capture.application.commands.save_reading_handler import SaveReadingHandler
from .posture_capture.application.queries.get_latest_reading_handler import (
    GetLatestReadingHandler,
)
from .posture_capture.application.queries.get_recent_readings_handler import (
    GetRecentReadingsHandler,
)
from .posture_capture.infrastructure.external.ml_client import MLServiceClient
from .posture_capture.infrastructure.persistence.mongo_posture_reading_repository import (
    MongoPostureReadingRepository,
)
from .posture_capture.interfaces.rest import readings_router
from .recommendations.application.applied_handlers import (
    ListAppliedRecommendationsHandler,
    MarkRecommendationAppliedHandler,
    UnmarkRecommendationAppliedHandler,
)
from .recommendations.infrastructure.persistence.mongo_applied_recommendation_repository import (
    MongoAppliedRecommendationRepository,
)
from .recommendations.interfaces.rest import recommendations_router as recommendations_router_mod
from .recommendations.interfaces.rest.recommendations_router import (
    router as recommendations_router,
)
from .session_history.application.commands.close_session_handler import CloseSessionHandler
from .session_history.application.commands.start_session_handler import StartSessionHandler
from .session_history.application.queries.get_session_handler import (
    GetActiveSessionHandler,
    GetSessionHandler,
)
from .session_history.application.queries.list_sessions_handler import ListSessionsHandler
from .session_history.infrastructure.external.readings_aggregator import (
    MongoReadingsAggregator,
)
from .session_history.infrastructure.persistence.mongo_session_repository import (
    MongoPostureSessionRepository,
)
from .session_history.interfaces.rest import sessions_router
from .shared.adapters import SessionStarterAdapter, VestLookupAdapter
from .shared.config import settings
from .shared.database import connect_database, disconnect_database, get_database
from .vest_management.application.commands.calibrate_vest_handler import (
    CalibrateVestHandler,
)
from .vest_management.application.commands.link_vest_handler import LinkVestHandler
from .vest_management.application.commands.register_vest_handler import (
    RegisterVestHandler,
)
from .vest_management.application.commands.send_command_handler import (
    SendVestCommandHandler,
)
from .vest_management.application.queries.get_my_vest_handler import GetMyVestHandler
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

    auth_router.set_register_handler(RegisterUserHandler(user_repo, password_service))
    auth_router.set_login_handler(LoginHandler(user_repo, password_service, token_service))
    auth_router.set_refresh_handler(RefreshTokenHandler(token_service))
    users_router.set_get_user_handler(GetUserHandler(user_repo))
    users_router.set_update_profile_handler(UpdateProfileHandler(user_repo))
    users_router.set_list_notifications_handler(ListNotificationsHandler(notif_repo))
    users_router.set_count_unread_handler(CountUnreadNotificationsHandler(notif_repo))
    users_router.set_mark_read_handler(MarkNotificationReadHandler(notif_repo))

    # ── Posture Capture
    posture_repo = MongoPostureReadingRepository(db)
    ml_client = MLServiceClient(settings.ml_service_url)
    save_reading_handler = SaveReadingHandler(posture_repo, ml_client)
    readings_router.set_handler(save_reading_handler)
    readings_router.set_latest_handler(GetLatestReadingHandler(posture_repo))
    readings_router.set_recent_handler(GetRecentReadingsHandler(posture_repo))

    # ── Vest Management
    vest_repo = MongoVestDeviceRepository(db)
    vests_router.set_register_handler(RegisterVestHandler(vest_repo))
    vests_router.set_link_handler(
        LinkVestHandler(
            vest_repo,
            password_service,
            expected_pairing_code=settings.vest_pairing_code or None,
        )
    )
    vests_router.set_calibrate_handler(CalibrateVestHandler(vest_repo))
    vests_router.set_get_my_vest_handler(GetMyVestHandler(vest_repo))

    # ── Recommendations (catálogo estático + persistencia de 'aplicadas')
    applied_recs_repo = MongoAppliedRecommendationRepository(db)
    recommendations_router_mod.set_mark_handler(
        MarkRecommendationAppliedHandler(applied_recs_repo)
    )
    recommendations_router_mod.set_unmark_handler(
        UnmarkRecommendationAppliedHandler(applied_recs_repo)
    )
    recommendations_router_mod.set_list_applied_handler(
        ListAppliedRecommendationsHandler(applied_recs_repo)
    )

    # ── Session History
    session_repo = MongoPostureSessionRepository(db)
    aggregator = MongoReadingsAggregator(db)
    start_session_handler = StartSessionHandler(session_repo)
    sessions_router.set_start_handler(start_session_handler)
    sessions_router.set_close_handler(CloseSessionHandler(session_repo, aggregator))
    sessions_router.set_get_handler(GetSessionHandler(session_repo))
    sessions_router.set_get_active_handler(GetActiveSessionHandler(session_repo))
    sessions_router.set_list_handler(ListSessionsHandler(session_repo))

    # ── MQTT (opcional, controlado por flag para que el dev local funcione sin broker)
    mqtt_subscriber = None
    if settings.mqtt_enabled and settings.mqtt_host:
        try:
            from .shared.mqtt import connect_mqtt, disconnect_mqtt
            from .vest_management.infrastructure.external.mqtt_vest_command_publisher import (
                MqttVestCommandPublisher,
            )
            from .posture_capture.interfaces.mqtt.posture_capture_subscriber import (
                PostureCaptureMqttSubscriber,
            )

            mqtt_client = await connect_mqtt()
            mqtt_publisher = MqttVestCommandPublisher(mqtt_client)
            vests_router.set_send_command_handler(
                SendVestCommandHandler(vest_repo, mqtt_publisher)
            )

            mqtt_subscriber = PostureCaptureMqttSubscriber(
                mqtt_client=mqtt_client,
                save_handler=save_reading_handler,
                vest_lookup=VestLookupAdapter(vest_repo),
                session_starter=SessionStarterAdapter(start_session_handler),
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


app = FastAPI(
    title="SitRight Backend API",
    description="API principal del sistema SitRight (FastAPI + MongoDB + MQTT)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(readings_router.router)
app.include_router(recommendations_router)
app.include_router(vests_router.router)
app.include_router(sessions_router.router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
