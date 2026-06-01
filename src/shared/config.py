from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "sitright"
    ml_service_url: str = "http://localhost:8001"

    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_expires_seconds: int = 3600
    jwt_refresh_expires_seconds: int = 1209600

    mqtt_host: str = ""
    mqtt_port: int = 8883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_client_id: str = "sitright-backend"
    mqtt_use_tls: bool = True
    mqtt_enabled: bool = False

    vest_pairing_code: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
