from pydantic import BaseModel


class RecommendationStepResponse(BaseModel):
    body: str
    meta: str


class RecommendationResponse(BaseModel):
    id: str
    number: str
    title: str
    description: str
    category: str
    icon: str
    frequency_label: str
    posture_classes: list[str]
    is_featured: bool = False
    featured_tagline: str | None = None
    featured_title_emphasis: str | None = None
    featured_body: str | None = None
    steps: list[RecommendationStepResponse] = []
