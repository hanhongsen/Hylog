"""
API 依赖注入

提供 FastAPI 的 Depends 依赖项：
- get_db：每个请求一个数据库会话，请求结束自动关闭
- get_mock_flag：从 .env 读取 USE_MOCK_AGENT 开关
- get_agent_path：返回数据库路径（供 ConversationAgent 使用）
"""

import os
from typing import Generator

from fastapi import Depends, HTTPException, Header

from src.data import get_session_local
from sqlalchemy.orm import Session


# ============================================================
# 配置读取
# ============================================================

def get_mock_flag() -> bool:
    """
    读取 .env 的 USE_MOCK_AGENT 开关

    用途：智谱余额不足时，可临时设为 true 切换 Mock 模式，
    验证 API 链路而不消耗余额。默认 false（真实模式）。

    返回:
        是否使用 Mock 模式
    """
    val = os.getenv("USE_MOCK_AGENT", "false").strip().lower()
    return val in ("true", "1", "yes", "on")


def get_db_path() -> str:
    """
    读取数据库路径（默认 hylog.db）

    返回:
        SQLite 数据库文件路径
    """
    return os.getenv("DB_PATH", "hylog.db")


# ============================================================
# 数据库会话依赖
# ============================================================

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖：每个请求一个数据库会话

    使用方式（在路由函数签名中）：
        @router.get("/...")
        def my_route(db: Session = Depends(get_db)):
            ...

    请求结束后会自动 close()，无需手动管理。
    若全局数据库未初始化（例如 startup 未触发或被 Mock 创建会话跳过），
    这里会自动用 DB_PATH 初始化一次，保证查询接口可用。
    """
    try:
        SessionLocal = get_session_local()
    except RuntimeError:
        # 全局未初始化，按需初始化一次
        from src.data import init_global_database, get_database_url
        db_path = get_db_path()
        init_global_database(get_database_url("sqlite", db_path))
        SessionLocal = get_session_local()

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# 会话状态恢复辅助函数（非 Depends，供路由内部调用）
# ============================================================

def load_session_or_404(db: Session, session_id: str):
    """
    加载会话记录，不存在则抛 404

    参数:
        db: 数据库会话
        session_id: 会话 ID

    返回:
        Session 模型实例

    异常:
        HTTPException(404): 会话不存在
    """
    from src.data import Session as SessionModel

    record = db.query(SessionModel).filter_by(session_id=session_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
    return record
