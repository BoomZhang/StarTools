from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "随手工具箱"
    app_env: str = "development"
    api_prefix: str = "/api"

    database_url: str = "postgresql+asyncpg://startools:startools@127.0.0.1:5432/startools"
    redis_url: str = "redis://127.0.0.1:6379/0"

    # 逗号分隔，例如：http://localhost:5173,http://127.0.0.1:5173
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    check_timeout: float = 2.0
    site_timezone: str = "Asia/Shanghai"

    # 管理台：部署时配置的单账号
    admin_username: str = "admin"
    admin_password: str = "startools-admin"
    jwt_secret: str = "startools-dev-jwt-secret-change-before-deploying"
    admin_session_hours: int = 8
    admin_cookie_name: str = "startools_admin"
    cookie_secure: bool = False
    login_max_failures: int = 5
    login_lock_minutes: int = 10

    # 存储与保留规则（R-03）
    storage_dir: str = "storage"
    raw_retention_days: int = 30
    result_retention_minutes: int = 60
    record_retention_days: int = 90
    disk_stop_percent: int = 80

    # 语音识别模型
    models_dir: str = "models"
    whisper_model_dir: str = "models/whisper"
    whisper_model_size: str = "base"
    hf_endpoint: str = "https://hf-mirror.com"

    # 限流（R-09）
    server_task_rate_per_hour: int = 30
    feedback_rate_per_hour: int = 5
    feedback_duplicate_minutes: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def storage_path(self) -> Path:
        path = Path(self.storage_dir)
        return path if path.is_absolute() else (BASE_DIR / path)

    @property
    def raw_path(self) -> Path:
        return self.storage_path / "raw"

    @property
    def result_path(self) -> Path:
        return self.storage_path / "results"

    @property
    def models_path(self) -> Path:
        path = Path(self.models_dir)
        return path if path.is_absolute() else (BASE_DIR / path)

    @property
    def whisper_model_path(self) -> Path:
        path = Path(self.whisper_model_dir)
        return path if path.is_absolute() else (BASE_DIR / path)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
