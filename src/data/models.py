"""
数据库模型定义

本文件定义了系统所需的所有数据库表结构，包括：
- User：用户表
- Session：会话表
- Message：对话记录表
- PersonalitySnapshot：人格快照表
- Result：结果表
- VerificationCode：验证码表
- Character：人物库表

使用 SQLAlchemy ORM 定义表结构。
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, JSON, ForeignKey
)
from sqlalchemy.orm import relationship, declarative_base

# 创建 SQLAlchemy 基类
Base = declarative_base()


# ============================================================
# 用户表
# ============================================================

class User(Base):
    """
    用户表
    
    存储用户的基本信息，支持多种登录方式：
    - 手机号 + 密码
    - 手机号 + 验证码
    - 微信登录
    - QQ 登录
    """
    
    __tablename__ = "users"  # 表名
    
    # ---------- 主键和基本信息 ----------
    user_id = Column(String(36), primary_key=True)    # 用户唯一标识（UUID）
    nickname = Column(String(50), nullable=False)      # 用户昵称
    avatar = Column(String(255), nullable=True)        # 头像 URL
    
    # ---------- 登录方式 ----------
    phone = Column(String(20), unique=True, nullable=True)      # 手机号（主登录方式）
    email = Column(String(100), unique=True, nullable=True)     # 邮箱（可选）
    password_hash = Column(String(255), nullable=True)          # 密码哈希值
    
    # ---------- 第三方登录 ----------
    wechat_openid = Column(String(100), unique=True, nullable=True)  # 微信 OpenID
    qq_openid = Column(String(100), unique=True, nullable=True)      # QQ OpenID
    
    # ---------- 状态和时间 ----------
    status = Column(String(20), default="active")      # 账号状态（active/banned/deleted）
    created_at = Column(DateTime, default=datetime.now)    # 注册时间
    last_login = Column(DateTime, nullable=True)           # 最后登录时间
    test_count = Column(Integer, default=0)                # 测试次数
    
    # ---------- 关联关系 ----------
    sessions = relationship("Session", back_populates="user")  # 关联的会话列表
    
    def __repr__(self):
        """对象的字符串表示"""
        return f"<User(user_id={self.user_id}, nickname={self.nickname})>"


# ============================================================
# 会话表
# ============================================================

class Session(Base):
    """
    会话表
    
    存储每次测试会话的信息，一个用户可以有多个会话。
    """
    
    __tablename__ = "sessions"
    
    # ---------- 主键 ----------
    session_id = Column(String(36), primary_key=True)    # 会话唯一标识（UUID）
    
    # ---------- 外键 ----------
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)  # 关联的用户
    
    # ---------- 会话状态 ----------
    status = Column(String(20), default="in_progress")   # 状态（in_progress/completed/interrupted）
    round_count = Column(Integer, default=0)             # 对话轮次
    current_module = Column(String(50), nullable=True)   # 当前探索的问题维度

    # ---------- 完整状态快照（用于运行时恢复） ----------
    # 存储 AgentState.to_dict() 的完整快照（OCEAN 向量、不确定性、对话历史、收敛详情等）
    # 每次 start/reply 后更新，下一次请求时通过 AgentState.from_dict() 恢复
    # 与 Message/PersonalitySnapshot 表职责分离：后者用于历史查询和人格演化展示
    state_json = Column(JSON, nullable=True)             # 完整 AgentState 序列化 JSON

    # ---------- 时间 ----------
    started_at = Column(DateTime, default=datetime.now)  # 开始时间
    ended_at = Column(DateTime, nullable=True)           # 结束时间
    
    # ---------- 关联关系 ----------
    user = relationship("User", back_populates="sessions")           # 关联的用户
    messages = relationship("Message", back_populates="session")     # 关联的对话记录
    snapshots = relationship("PersonalitySnapshot", back_populates="session")  # 关联的人格快照
    result = relationship("Result", back_populates="session", uselist=False)   # 关联的结果（一对一）
    
    def __repr__(self):
        return f"<Session(session_id={self.session_id}, status={self.status})>"


# ============================================================
# 对话记录表
# ============================================================

class Message(Base):
    """
    对话记录表
    
    存储会话中的每一轮对话，包括用户回答和 AI 回复。
    """
    
    __tablename__ = "messages"
    
    # ---------- 主键 ----------
    message_id = Column(String(36), primary_key=True)    # 消息唯一标识（UUID）
    
    # ---------- 外键 ----------
    session_id = Column(String(36), ForeignKey("sessions.session_id"), nullable=False)
    
    # ---------- 消息内容 ----------
    role = Column(String(20), nullable=False)            # 角色（user/assistant）
    content = Column(Text, nullable=False)               # 消息内容
    module = Column(String(50), nullable=True)           # 该问题所属维度
    
    # ---------- AI 分析结果 ----------
    ocean_delta = Column(JSON, nullable=True)            # 该回答对 OCEAN 的影响值
    
    # ---------- 时间 ----------
    created_at = Column(DateTime, default=datetime.now)
    
    # ---------- 关联关系 ----------
    session = relationship("Session", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(message_id={self.message_id}, role={self.role})>"


# ============================================================
# 人格快照表
# ============================================================

class PersonalitySnapshot(Base):
    """
    人格快照表
    
    存储每次更新时的人格状态快照，用于：
    1. 记录人格演化过程
    2. 支持可视化
    3. 用于收敛判断
    """
    
    __tablename__ = "personality_snapshots"
    
    # ---------- 主键 ----------
    snapshot_id = Column(String(36), primary_key=True)   # 快照唯一标识（UUID）
    
    # ---------- 外键 ----------
    session_id = Column(String(36), ForeignKey("sessions.session_id"), nullable=False)
    
    # ---------- 快照数据 ----------
    round = Column(Integer, nullable=False)              # 第几轮对话后
    
    # OCEAN 数据
    ocean_vector = Column(JSON, nullable=False)          # OCEAN 五维分数
    ocean_uncertainty = Column(JSON, nullable=False)     # OCEAN 不确定性
    
    # 11 维数据
    dim11_vector = Column(JSON, nullable=False)          # 11 维分数
    dim11_uncertainty = Column(JSON, nullable=False)     # 11 维不确定性
    dim11_explore_count = Column(JSON, nullable=False)   # 11 维探索次数
    
    # ---------- 时间 ----------
    created_at = Column(DateTime, default=datetime.now)
    
    # ---------- 关联关系 ----------
    session = relationship("Session", back_populates="snapshots")
    
    def __repr__(self):
        return f"<PersonalitySnapshot(snapshot_id={self.snapshot_id}, round={self.round})>"


# ============================================================
# 结果表
# ============================================================

class Result(Base):
    """
    结果表
    
    存储测试完成后的最终结果，包括匹配的人物和原因解释。
    """
    
    __tablename__ = "results"
    
    # ---------- 主键 ----------
    result_id = Column(String(36), primary_key=True)     # 结果唯一标识（UUID）
    
    # ---------- 外键 ----------
    session_id = Column(String(36), ForeignKey("sessions.session_id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    
    # ---------- 最终人格向量 ----------
    final_ocean = Column(JSON, nullable=False)           # 最终 OCEAN 向量
    final_dim11 = Column(JSON, nullable=False)          # 最终 11 维向量
    
    # ---------- 匹配结果 ----------
    matched_character_id = Column(String(36), nullable=False)      # 匹配的人物 ID
    matched_character_name = Column(String(100), nullable=False)   # 匹配的人物名称
    matched_character_source = Column(String(50), nullable=False)  # 人物来源
    matched_similarity = Column(Float, nullable=False)             # 相似度分数
    
    # ---------- 候选人物 ----------
    candidate_characters = Column(JSON, nullable=True)   # 候选人物（Top-K）
    
    # ---------- 匹配原因 ----------
    match_reason = Column(Text, nullable=True)           # 匹配原因解释（AI 生成）
    
    # ---------- 时间 ----------
    created_at = Column(DateTime, default=datetime.now)
    
    # ---------- 关联关系 ----------
    session = relationship("Session", back_populates="result")
    
    def __repr__(self):
        return f"<Result(result_id={self.result_id}, matched={self.matched_character_name})>"


# ============================================================
# 验证码表
# ============================================================

class VerificationCode(Base):
    """
    验证码表
    
    存储验证码信息，用于：
    1. 手机验证码登录
    2. 密码找回
    3. 绑定手机/邮箱
    """
    
    __tablename__ = "verification_codes"
    
    # ---------- 主键 ----------
    code_id = Column(String(36), primary_key=True)      # 验证码唯一标识（UUID）
    
    # ---------- 验证码信息 ----------
    target = Column(String(100), nullable=False)        # 目标（手机号或邮箱）
    code = Column(String(10), nullable=False)           # 验证码
    code_type = Column(String(20), nullable=False)      # 类型（login/register/reset_password/bind）
    
    # ---------- 状态 ----------
    used = Column(Boolean, default=False)               # 是否已使用
    
    # ---------- 时间 ----------
    expires_at = Column(DateTime, nullable=False)       # 过期时间
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<VerificationCode(code_id={self.code_id}, type={self.code_type})>"


# ============================================================
# 人物库表
# ============================================================

class Character(Base):
    """
    人物库表

    存储所有可用于匹配的人物信息。

    注意：当前人物库只包含中国历史上的真实人物（清朝或之前），
    不包含文学虚构人物、影视角色、神话人物、近现代人物。
    """

    __tablename__ = "characters"

    # ---------- 主键 ----------
    character_id = Column(String(36), primary_key=True)  # 人物唯一标识（UUID）

    # ---------- 基本信息 ----------
    name = Column(String(100), nullable=False)           # 人物名称
    source = Column(String(50), nullable=False)          # 来源（历史）
    era = Column(String(50), nullable=True)              # 年代/时期（历史人物必填，如"唐朝"、"三国"）
    description = Column(Text, nullable=True)            # 人物简介生平（100-200字）
    
    # ---------- 人格向量 ----------
    ocean_vector = Column(JSON, nullable=False)          # 预标注的 OCEAN 向量
    
    # ---------- 基础展示字段（免费可见） ----------
    image_path = Column(String(255), nullable=True)      # 人物图片本地路径
    
    # ---------- 付费解锁字段 ----------
    tags = Column(JSON, nullable=True)                   # 标签列表（5个）
    quote = Column(Text, nullable=True)                  # 语录/名言/成语/评价
    personality_keyword = Column(String(50), nullable=True)  # 性格关键词（如"智慧谨慎型"）
    classic_events = Column(Text, nullable=True)         # 经典场景/事件
    fun_facts = Column(Text, nullable=True)              # 趣味冷知识
    advice = Column(Text, nullable=True)                 # 性格建议
    related_books = Column(Text, nullable=True)          # 相关书籍
    
    # ---------- 统计和状态 ----------
    match_count = Column(Integer, default=0)             # 匹配次数（用于计算热度）
    is_active = Column(Boolean, default=True)            # 是否可用（可禁用某些人物）
    
    # ---------- 时间 ----------
    created_at = Column(DateTime, default=datetime.now)  # 创建时间
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)  # 更新时间
    
    def __repr__(self):
        return f"<Character(character_id={self.character_id}, name={self.name})>"


# ============================================================
# 辅助函数
# ============================================================

def create_tables(engine):
    """
    创建所有数据库表
    
    参数:
        engine: SQLAlchemy 引擎对象
    """
    Base.metadata.create_all(engine)


def drop_tables(engine):
    """
    删除所有数据库表
    
    参数:
        engine: SQLAlchemy 引擎对象
    """
    Base.metadata.drop_all(engine)
