import httpx

from ...domain.entities.posture_reading import PostureReading


class MLServiceClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def classify(self, reading: PostureReading) -> tuple[str, float]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{self._base_url}/ml/classify",
                json={
                    "cervical": [reading.cervical.ax, reading.cervical.ay, reading.cervical.az],
                    "dorsal": [reading.dorsal.ax, reading.dorsal.ay, reading.dorsal.az],
                    "lumbar": [reading.lumbar.ax, reading.lumbar.ay, reading.lumbar.az],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["class"], data["confidence"]
