from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase

from ....posture_capture.domain.value_objects.sensor_data import SensorData
from ....shared.datetime_utils import parse_utc
from ...domain.entities.training_sample import TrainingSample


class MongoTrainingSampleRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["training_samples"]

    async def save_many(self, samples: list[TrainingSample]) -> None:
        if not samples:
            return
        await self._col.insert_many([self._to_doc(s) for s in samples])

    async def list_all(self) -> list[TrainingSample]:
        cursor = self._col.find().sort("captured_at", 1)
        return [self._from_doc(doc) async for doc in cursor]

    async def counts(self) -> dict:
        by_label: dict[str, int] = {}
        by_subject: dict[str, int] = {}
        total = 0
        async for doc in self._col.find({}, {"label": 1, "subject": 1}):
            total += 1
            by_label[doc["label"]] = by_label.get(doc["label"], 0) + 1
            by_subject[doc["subject"]] = by_subject.get(doc["subject"], 0) + 1
        return {"total": total, "by_label": by_label, "by_subject": by_subject}

    @staticmethod
    def _triple_doc(s: SensorData) -> dict:
        return {"ax": s.ax, "ay": s.ay, "az": s.az}

    def _to_doc(self, s: TrainingSample) -> dict:
        return {
            "_id": str(s.id),
            "subject": s.subject,
            "label": s.label,
            "cervical": self._triple_doc(s.cervical),
            "dorsal": self._triple_doc(s.dorsal),
            "lumbar": self._triple_doc(s.lumbar),
            "captured_at": s.captured_at.isoformat(),
            "created_by": str(s.created_by),
        }

    @staticmethod
    def _sensor(d: dict) -> SensorData:
        return SensorData(d["ax"], d["ay"], d["az"])

    def _from_doc(self, doc: dict) -> TrainingSample:
        return TrainingSample(
            id=UUID(doc["_id"]),
            subject=doc["subject"],
            label=doc["label"],
            cervical=self._sensor(doc["cervical"]),
            dorsal=self._sensor(doc["dorsal"]),
            lumbar=self._sensor(doc["lumbar"]),
            captured_at=parse_utc(doc["captured_at"]),
            created_by=UUID(doc["created_by"]),
        )
