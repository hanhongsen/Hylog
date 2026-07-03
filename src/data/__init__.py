"""
数据模块

本模块提供数据库连接和数据模型，包括：
- 数据库连接管理
- 所有数据模型类
- 数据库初始化函数
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
    # 创建引擎
    engine = create_engine(database_url, echo=False)
    
    # 创建所有表
    create_tables(engine)
    
    # 创建会话工厂
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return engine, SessionLocal


def get_session(SessionLocal):
    """
    获取数据库会话
    
    参数:
        SessionLocal: 会话工厂
    
    返回:
        数据库会话对象
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
