import csv
import io
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from ....iam.domain.services.token_service import TokenPayload
from ....iam.interfaces.rest.dependencies import require_admin
from ....posture_capture.domain.value_objects.sensor_data import SensorData
from ....shared.datetime_utils import now_utc
from ...domain.entities.training_sample import TrainingSample
from ...domain.repositories.training_sample_repository import TrainingSampleRepository

router = APIRouter(prefix="/api/v1/training", tags=["training_data"])

ALLOWED_LABELS = {"adequate", "forward_slouch", "excessive_recline", "neutral"}

_repository: TrainingSampleRepository | None = None


def set_repository(repository: TrainingSampleRepository) -> None:
    global _repository
    _repository = repository


def get_repository() -> TrainingSampleRepository:
    if _repository is None:
        raise RuntimeError("TrainingSampleRepository no inicializado")
    return _repository


class SampleIn(BaseModel):
    subject: str = Field(..., min_length=1, max_length=64)
    label: str
    cervical: list[float] = Field(..., min_length=3, max_length=3)
    dorsal: list[float] = Field(..., min_length=3, max_length=3)
    lumbar: list[float] = Field(..., min_length=3, max_length=3)


class SamplesBatchIn(BaseModel):
    samples: list[SampleIn] = Field(..., min_length=1, max_length=5000)


@router.post("/samples", status_code=201, summary="Guardar muestras etiquetadas (solo admin)")
async def save_samples(
    body: SamplesBatchIn,
    current: Annotated[TokenPayload, Depends(require_admin)],
    repository: Annotated[TrainingSampleRepository, Depends(get_repository)],
) -> dict:
    now = now_utc()
    samples: list[TrainingSample] = []
    for s in body.samples:
        if s.label not in ALLOWED_LABELS:
            raise HTTPException(
                status_code=400,
                detail=f"Etiqueta inválida: {s.label}. Válidas: {sorted(ALLOWED_LABELS)}",
            )
        samples.append(
            TrainingSample(
                id=uuid4(),
                subject=s.subject.strip(),
                label=s.label,
                cervical=SensorData(*s.cervical),
                dorsal=SensorData(*s.dorsal),
                lumbar=SensorData(*s.lumbar),
                captured_at=now,
                created_by=current.user_id,
            )
        )
    await repository.save_many(samples)
    return {"saved": len(samples)}


@router.get("/samples/stats", summary="Conteo de muestras por clase y sujeto (solo admin)")
async def sample_stats(
    current: Annotated[TokenPayload, Depends(require_admin)],
    repository: Annotated[TrainingSampleRepository, Depends(get_repository)],
) -> dict:
    return await repository.counts()


@router.get("/samples/export", summary="Exportar el dataset como CSV (solo admin)")
async def export_samples(
    current: Annotated[TokenPayload, Depends(require_admin)],
    repository: Annotated[TrainingSampleRepository, Depends(get_repository)],
) -> Response:
    rows = await repository.list_all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id", "subject", "label",
            "cervical_ax", "cervical_ay", "cervical_az",
            "dorsal_ax", "dorsal_ay", "dorsal_az",
            "lumbar_ax", "lumbar_ay", "lumbar_az",
            "captured_at",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                str(r.id), r.subject, r.label,
                r.cervical.ax, r.cervical.ay, r.cervical.az,
                r.dorsal.ax, r.dorsal.ay, r.dorsal.az,
                r.lumbar.ax, r.lumbar.ay, r.lumbar.az,
                r.captured_at.isoformat(),
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=training_samples.csv"},
    )
