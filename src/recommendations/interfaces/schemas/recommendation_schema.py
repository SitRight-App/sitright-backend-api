from pydantic import BaseModel


class RecommendationResponse(BaseModel):
    title: str
    description: str
