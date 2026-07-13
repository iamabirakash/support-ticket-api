from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MAX_QUEUES: int = 10
    MAX_TICKETS_PER_QUEUE: int | None = None
    STANDARD_EFFORT_BLOCKS: list[int] = [1, 2, 5, 10, 20, 50, 100]
    METRIC: str = "POINTS"
    DATABASE_URL: str = "sqlite:///./support.db"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
