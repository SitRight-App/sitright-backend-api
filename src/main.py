from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .posture_capture.infrastructure.external.ml_client import MLServiceClient
from .posture_capture.infrastructure.persistence.mongo_posture_reading_repository import (
    MongoPostureReadingRepository,
)
from .posture_capture.application.commands.save_reading_handler import SaveReadingHandler
from .posture_capture.application.queries.get_latest_reading_handler import GetLatestReadingHandler
from .posture_capture.interfaces.rest import readings_router
from .recommendations.interfaces.rest.recommendations_router import router as recommendations_router
from .shared.config import settings
from .shared.database import connect_database, disconnect_database, get_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_database()
    db = get_database()
    repo = MongoPostureReadingRepository(db)
    ml_client = MLServiceClient(settings.ml_service_url)
    readings_router.set_handler(SaveReadingHandler(repo, ml_client))
    readings_router.set_latest_handler(GetLatestReadingHandler(repo))
    yield
    await disconnect_database()


app = FastAPI(
    title="SitRight Backend API",
    description="API principal del sistema SitRight — FastAPI + MongoDB",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(readings_router.router)
app.include_router(recommendations_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
