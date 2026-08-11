from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "制度智能审查系统 API"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://policy:policy@localhost:5432/policy_review"
    session_cookie_name: str = "policy_session"
    cookie_secure: bool = False
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    bootstrap_demo_data: bool = True
    file_storage_root: str = "storage"
    retrieval_top_k: int = 20
    rrf_k: int = 60
    llm_api_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    llm_api_key: str = ""
    llm_chat_model: str = "glm-4.7"
    llm_timeout_seconds: float = 120
    llm_thinking_enabled: bool = True
    llm_max_tokens: int = 8192

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
