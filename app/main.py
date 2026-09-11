"""FastAPI 应用入口。

- 自动生成 OpenAPI 契约：/openapi.json、Swagger UI: /docs、Redoc: /redoc
- 内置后台管理静态 UI（纯 HTML/CSS/JS，仅通过 REST API 与后端交互，可随时替换）
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import (
    admin_backup,
    admin_customers,
    admin_fields,
    admin_projects,
    admin_settings,
    auth,
    public,
    v1,
)
from app.config import settings
from app.database import init_db

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表 + 初始化管理员
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "## 通用客户信息管理系统\n\n"
        "- 后台管理接口（`/api/admin/*`）：后台 UI 登录后使用，鉴权方式为 **账号密码换取 JWT Bearer Token**\n"
        "- 公开表单接口（`/api/public/*`）：供客户填报，无需鉴权\n"
        "- 集成接口（`/api/v1/*`）：供独立部署 / 替换的前端使用，"
        "通过请求头 **`X-API-Token`** 鉴权，Token 由环境变量 `API_TOKEN` 配置\n\n"
        "项目、表单字段均为动态配置，前端根据 `/form` 返回的字段定义自动生成表单。"
    ),
    lifespan=lifespan,
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由（注意：API 路由必须在 StaticFiles 挂载之前注册）
app.include_router(auth.router)
app.include_router(admin_projects.router)
app.include_router(admin_fields.router)
app.include_router(admin_customers.router)
app.include_router(admin_backup.router)
app.include_router(admin_settings.router)
app.include_router(public.router)
app.include_router(v1.router)


@app.get("/health", tags=["系统"], summary="健康检查")
def health():
    return {"status": "ok"}


# 内置后台 UI 与客户填报表单页（静态资源，纯前端，与后端通过 API 解耦）
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
