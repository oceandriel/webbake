"""后台 - SQLite 数据库备份下载 / 本地恢复上传。

- 备份：使用 sqlite3 在线备份 API 生成一致性快照，通过浏览器下载到本地；
- 恢复：上传本地 .db 文件，校验文件头 / 完整性 / 必备表后在线热替换。
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import database
from app.api.deps import get_current_user, get_db
from app.config import settings

router = APIRouter(prefix="/api/admin/database", tags=["数据备份"], dependencies=[Depends(get_current_user)])

MAX_RESTORE_BYTES = 200 * 1024 * 1024
REQUIRED_TABLES = {"users", "projects", "fields", "customers"}
SQLITE_HEADER = b"SQLite format 3\x00"

_restore_lock = threading.Lock()


@router.get("/backup", summary="备份数据库（下载 .db 到本地）")
def backup_database():
    db_path = database.sqlite_path(settings.database_url)
    if not db_path or db_path == ":memory:":
        raise HTTPException(status_code=400, detail="当前数据库不是文件型 SQLite，无法备份")
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="数据库文件不存在")

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    # 以只读方式打开在线库，用 backup API 拷贝一致性快照
    source_uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    source = sqlite3.connect(source_uri, uri=True)
    target = sqlite3.connect(tmp.name)
    try:
        source.backup(target)
        target.close()
    finally:
        source.close()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return FileResponse(
        tmp.name,
        media_type="application/octet-stream",
        filename=f"cims-backup-{stamp}.db",
    )


@router.post("/restore", summary="从本地 .db 文件恢复数据库")
async def restore_database(file: UploadFile, db: Session = Depends(get_db)):
    db_path = database.sqlite_path(settings.database_url)
    if not db_path or db_path == ":memory:":
        raise HTTPException(status_code=400, detail="当前数据库不是文件型 SQLite，无法恢复")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(content) > MAX_RESTORE_BYTES:
        raise HTTPException(status_code=413, detail="备份文件过大（上限 200MB）")
    if not content.startswith(SQLITE_HEADER):
        raise HTTPException(status_code=400, detail="不是合法的 SQLite 数据库文件")

    # 先写入临时文件并做完整性 / 表结构校验
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    try:
        tmp.write(content)
        tmp.close()
        _verify_backup_file(tmp.name)

        with _restore_lock:
            # 关闭当前请求使用的会话与连接池，释放文件锁
            db.close()
            database.engine.dispose()
            shutil.copyfile(tmp.name, db_path)
            # 清理可能残留的辅助文件
            for suffix in ("-journal", "-wal", "-shm"):
                extra = db_path + suffix
                if os.path.exists(extra):
                    os.remove(extra)
            # 重新绑定引擎并补齐缺失的表
            database.rebind_engine(settings.database_url)
            database.init_db()
    finally:
        if os.path.exists(tmp.name):
            os.remove(tmp.name)

    return {"ok": True, "message": "数据库已从本地备份恢复"}


def _verify_backup_file(path: str) -> None:
    conn = sqlite3.connect(path)
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        if not row or row[0] != "ok":
            raise HTTPException(status_code=400, detail="备份文件完整性校验失败")
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        missing = REQUIRED_TABLES - tables
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"备份文件缺少系统表: {', '.join(sorted(missing))}，拒绝恢复",
            )
    finally:
        conn.close()
