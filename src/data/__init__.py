"""
数据模块

本模块提供数据库连接和数据模型，包括：
- 数据库连接管理
- 所有数据模型类
- 数据库初始化函数
- 全局引擎单例（供 FastAPI 等 Web 场景复用，避免每次请求新建 engine）
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 导出所有数据模型
from .models import (
    Base,
    User,
    Session,
    Message,
    PersonalitySnapshot,
    Result,
    VerificationCode,
    Character,
    create_tables,
    drop_tables
)


# ============================================================
# 数据库连接配置
# ============================================================

def get_database_url(database_type: str = "sqlite", database_path: str = "hylog.db") -> str:
    """
    获取数据库连接 URL

    参数:
        database_type: 数据库类型（sqlite/mysql/postgresql）
        database_path: 数据库路径或名称

    返回:
        数据库连接 URL 字符串
    """
    if database_type == "sqlite":
        return f"sqlite:///{database_path}"
    elif database_type == "mysql":
        return f"mysql+pymysql://user:password@localhost/{database_path}"
    elif database_type == "postgresql":
        return f"postgresql://user:password@localhost/{database_path}"
    else:
        return f"sqlite:///{database_path}"


def init_database(database_url: str):
    """
    初始化数据库

    参数:
        database_url: 数据库连接 URL

    返回:
        (engine, SessionLocal) 元组
    """
    # SQLite 需要禁用线程检查（FastAPI/uvicorn 在多线程下访问 SQLite 会报错）
    # 这是 SQLite + Web 框架的标准配置
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    # 创建引擎
    engine = create_engine(database_url, echo=False, connect_args=connect_args)

    # 创建所有表
    create_tables(engine)

    # 创建会话工厂
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    return engine, SessionLocal


# ============================================================
# 全局引擎单例（供 FastAPI 等场景复用）
# ============================================================

# 全局 engine 和 SessionLocal，应用启动时初始化一次
_global_engine = None
_global_SessionLocal = None


def init_global_database(database_url: str):
    """
    初始化全局数据库单例（应用启动时调用一次）

    与 init_database() 的区别：
    - init_database() 每次调用都新建 engine（适合脚本场景）
    - init_global_database() 只初始化一次，全局复用（适合 Web 场景，避免连接泄露）

    参数:
        database_url: 数据库连接 URL

    返回:
        (engine, SessionLocal) 元组
    """
    global _global_engine, _global_SessionLocal
    if _global_engine is None:
        _global_engine, _global_SessionLocal = init_database(database_url)
    return _global_engine, _global_SessionLocal


def get_engine():
    """
    获取全局 engine（需先调用 init_global_database）

    返回:
        SQLAlchemy engine 实例
    """
    if _global_engine is None:
        raise RuntimeError("数据库未初始化，请先调用 init_global_database()")
    return _global_engine


def get_session_local():
    """
    获取全局 SessionLocal 工厂（需先调用 init_global_database）

    返回:
        sessionmaker 实例
    """
    if _global_SessionLocal is None:
        raise RuntimeError("数据库未初始化，请先调用 init_global_database()")
    return _global_SessionLocal


def get_session(SessionLocal):
    """
    获取数据库会话（生成器，适合直接用 next() 或 for 循环）

    参数:
        SessionLocal: 会话工厂

    返回/生成:
        数据库会话对象
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
