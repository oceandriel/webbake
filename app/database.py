"""数据库引擎、会话工厂与初始化。

注意：全项目只有这一个 DeclarativeBase（Base），所有模型都继承它，
避免重复 declarative_base 导致 create_all() 不建表的问题。
"""

from __future__ import annotations

import json
import os

from sqlalchemy import create_engine, event, make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _json_dumps(value) -> str:
    # ensure_ascii=False：让中文原样入库，SQLite LIKE 才能直接搜索中文
    return json.dumps(value, ensure_ascii=False)


class Base(DeclarativeBase):
    pass


def _sqlite_connect_listener(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    # 显式使用 DELETE 日志模式，保证备份/恢复时直接拷贝单个 .db 文件即可
    cursor.execute("PRAGMA journal_mode=DELETE")
    cursor.close()


def make_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    eng = create_engine(
        database_url,
        connect_args=connect_args,
        future=True,
        json_serializer=_json_dumps,
    )
    if database_url.startswith("sqlite"):
        event.listens_for(eng, "connect")(_sqlite_connect_listener)
    return eng


engine = make_engine(settings.database_url)

# 全局唯一会话工厂；恢复数据库时通过 SessionLocal.configure(bind=) 重新绑定
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def sqlite_path(database_url: str) -> str | None:
    """从 SQLAlchemy URL 中解析 SQLite 文件路径（:memory: 返回 ':memory:'）。"""
    if not database_url.startswith("sqlite"):
        return None
    return make_url(database_url).database


def ensure_data_dir(database_url: str) -> None:
    path = sqlite_path(database_url)
    if path and path != ":memory:":
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def rebind_engine(database_url: str) -> None:
    """恢复数据库后释放旧连接池并用新引擎重新绑定全局会话工厂。"""
    global engine
    engine.dispose()
    engine = make_engine(database_url)
    SessionLocal.configure(bind=engine)


def _run_lightweight_migrations() -> None:
    """对已存在的 SQLite 库做向后兼容的补列迁移（SQLAlchemy create_all 不会改已有表）。"""
    if not settings.database_url.startswith("sqlite"):
        return
    from sqlalchemy import text

    additions = {
        "projects": [
            ("notify_enabled", "BOOLEAN NOT NULL DEFAULT 0"),
            ("notify_emails", "JSON NOT NULL DEFAULT '[]'"),
        ],
    }
    with engine.begin() as conn:
        for table, columns in additions.items():
            existing = {
                row[1]
                for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            }
            if not existing:
                # 表尚不存在，create_all 会按最新模型创建
                continue
            for column, ddl in columns:
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def init_db() -> None:
    # 导入模型以注册到同一套 Base.metadata
    from app import models  # noqa: F401
    from app.core.security import hash_password
    from app.models.user import User

    ensure_data_dir(settings.database_url)
    Base.metadata.create_all(bind=engine)
    _run_lightweight_migrations()

    # 初始化管理员账号（用户表为空时）
    with SessionLocal() as db:
        if db.query(User).count() == 0:
            db.add(
                User(
                    username=settings.admin_username,
                    hashed_password=hash_password(settings.admin_password),
                )
            )
            db.commit()
