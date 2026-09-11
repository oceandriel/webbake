"""应用配置：全部通过环境变量（或本地 .env）注入。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "通用客户信息管理系统"

    # SQLite 连接串。本地默认 ./data/cims.db；容器内默认 /data/cims.db（Dockerfile 注入）
    database_url: str = "sqlite:///./data/cims.db"

    # JWT 签名密钥
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 720

    # 后台初始管理员（仅在用户表为空时初始化一次）
    admin_username: str = "admin"
    admin_password: str = "admin123456"

    # 外部集成 API Token：无 UI，改环境变量重启即更换
    api_token: str = "change-me-api-token"

    # CORS：逗号分隔，* 表示全部放行（独立部署的前端跨域访问）
    cors_origins: str = "*"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
