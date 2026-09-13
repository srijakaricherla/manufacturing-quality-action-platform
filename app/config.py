from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./quality.db"
    kafka_bootstrap_servers: str = "localhost:19092"
    kafka_topic: str = "quality-events"
    action_failure_rate: float = 0.0
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

