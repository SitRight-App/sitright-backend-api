from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "sitright"
    ml_service_url: str = "http://localhost:8001"
    jwt_secret: str = "dev-secret-change-in-production"

    model_config = {"env_file": ".env"}


settings = Settings()
