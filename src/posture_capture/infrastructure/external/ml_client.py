import httpx

from ...domain.entities.posture_reading import PostureReading


class MLServiceClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def classify(self, reading: PostureReading) -> tuple[str, float]:
        # HU-04 AC4 — el AC exige timeout de 2 s. Si el ml-service no
        # responde dentro de ese plazo, el SaveReadingHandler captura la
        # excepción y la lectura queda como 'indeterminate'.
        async with httpx.AsyncClient(timeout=2.0) as client:
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
