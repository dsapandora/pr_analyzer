from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""

    # JWT
    jwt_secret_key: str = "changeme-use-a-real-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Rocketride
    rocketride_uri: str = "ws://localhost:5565"
    rocketride_apikey: str = ""
    rocketride_analyze_pipeline: str = "pr_analyzer"
    rocketride_chat_pipeline: str = "pr_chat"
    rocketride_criteria_pipeline: str = "commit_criteria"

    # Commit criteria ingestion
    criteria_repo: str = "rocketride-io/rocketride-server"
    criteria_authors: list[str] = [
        "dmitry.karataev@gmail.com",
        "asclearuc@gmail.com",
        "98939082+Rod-Christensen@users.noreply.github.com",
        "stepmikhaylov@yandex.ru",
        "ariel@lazyracoon.tech",
    ]

    @property
    def rocketride_url(self) -> str:
        uri = self.rocketride_uri
        return uri.replace("http://", "ws://").replace("https://", "wss://")

    @property
    def rocketride_api_key(self) -> str:
        return self.rocketride_apikey

    @property
    def rocketride_pipeline(self) -> str:
        return self.rocketride_analyze_pipeline

    # Database (JawsDB Maria on Heroku or local MariaDB/MySQL)
    # JawsDB sets JAWSDB_MARIA_URL automatically; fallback to DATABASE_URL or local
    database_url: str = "mysql://root:@localhost:3306/pr_analyzer"
    jawsdb_maria_url: Optional[str] = None  # Heroku sets this automatically

    @property
    def db_url(self) -> str:
        return self.jawsdb_maria_url or self.database_url

    # Qdrant Cloud (vectors only)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_collection: str = "pr_analyzer"

    # LLM providers (env: ANTHROPIC_API_KEY or ANTHROPIC_APIKEY — sin guión bajo antes de KEY)
    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OPENAI_API_KEY", "ROCKETRIDE_OPENAI_KEY"),
    )
    anthropic_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "ANTHROPIC_APIKEY"),
    )
    # Optional; same secret for RocketRide ${ROCKETRIDE_ANTHROPIC_APIKEY} if not using ANTHROPIC_API_KEY
    rocketride_anthropic_apikey: str = ""

    # App settings
    cors_origins: list[str] = ["http://localhost:3000", "https://your-app.herokuapp.com"]
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
