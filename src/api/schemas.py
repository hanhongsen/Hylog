"""
API 数据模型（Pydantic）

本文件定义所有 API 接口的请求/响应数据结构。
FastAPI 会基于这些模型自动生成请求校验和 Swagger 文档。

设计原则：
- 请求模型严格校验（如 answer 长度 1~100 字符）
- 响应模型与 ConversationAgent._build_response() 的返回结构对齐
- 付费字段（quote/advice 等）暂时全部返回，后续加付费分层时再裁剪
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# ============================================================
# 请求模型
# ============================================================

class CreateSessionRequest(BaseModel):
    """创建会话请求"""

    user_id: Optional[str] = Field(
        default=None,
        description="用户 ID。不传则使用临时假用户（认证功能上线前用）",
        examples=["test-user-001"],
    )


class ReplyRequest(BaseModel):
    """提交回答请求"""

    answer: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="用户的回答文本，1~100 字符（超出会返回 422 校验错误）",
        examples=["我喜欢一个人安静地看书"],
    )


# ============================================================
# 响应模型 - 公共子结构
# ============================================================

class ProgressInfo(BaseModel):
    """对话进度信息（供前端展示已答几轮、覆盖率等）"""

    turn: int = Field(..., description="有效对话轮次")
    min_rounds: int = Field(..., description="最小收敛轮次")
    max_rounds: int = Field(..., description="最大轮次上限（兜底）")
    dimension_coverage: str = Field(..., description="维度覆盖率，如 '8/11'")
    converged: bool = Field(..., description="是否已收敛")


class CharacterBrief(BaseModel):
    """
    人物基础信息（免费可见层）

    与 CharacterData.to_dict() 的基础字段对齐。
    """

    character_id: str
    name: str
    source: str
    era: str = ""
    description: str = ""
    image_path: str = ""
    ocean_vector: Dict[str, float] = Field(
        default_factory=lambda: {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5}
    )
    # 付费字段（暂全部返回，后续付费分层时根据请求身份裁剪）
    tags: List[str] = Field(default_factory=list)
    quote: str = ""
    personality_keyword: str = ""
    classic_events: str = ""
    fun_facts: str = ""
    advice: str = ""
    related_books: str = ""


class MatchResultInfo(BaseModel):
    """匹配结果"""

    character: CharacterBrief
    similarity: float = Field(..., description="相似度（0~1）")
    similarity_percent: int = Field(..., description="相似度百分比")
    heat_level: str = Field(..., description="热度等级名称，如 '热门'")
    heat_percent: int = Field(..., description="热度百分比排名")
    is_paid_locked: bool = Field(..., description="付费字段是否锁定（当前始终 False）")


# ============================================================
# 响应模型 - 主响应
# ============================================================

class ConversationResponse(BaseModel):
    """
    对话响应（start / reply 通用）

    与 ConversationAgent._build_response() 返回结构对齐。
    """

    session_id: str = Field(..., description="会话 ID")
    question: Optional[str] = Field(
        default=None,
        description="返回给用户的消息（开场白+问题 / 下一个问题 / 匹配结果）。已结束的会话为 null",
    )
    message: Optional[str] = Field(
        default=None,
        description="提示消息（已结束会话时为 '本次测试已完成'）",
    )
    personality_state: Dict[str, float] = Field(
        ...,
        description="当前 OCEAN 五维分数，如 {'O': 0.62, 'C': 0.55, 'E': 0.32, 'A': 0.58, 'N': 0.32}",
    )
    progress: ProgressInfo
    is_finished: bool = Field(..., description="本次测试是否已完成")
    forced_finish: bool = Field(..., description="是否因达到最大轮次而强制结束")
    result: Optional[MatchResultInfo] = Field(
        default=None,
        description="匹配结果。仅 is_finished=True 时有值",
    )


class SessionStateResponse(BaseModel):
    """会话状态摘要（GET /state 返回）"""

    session_id: str
    personality_state: Dict[str, float]
    progress: ProgressInfo
    is_finished: bool
    result: Optional[MatchResultInfo] = None


class MessageItem(BaseModel):
    """单条对话消息（GET /messages 返回）"""

    message_id: str
    role: str = Field(..., description="角色：user / assistant")
    content: str
    module: Optional[str] = Field(default=None, description="该问题所属维度")
    ocean_delta: Optional[Dict[str, float]] = Field(
        default=None,
        description="该回答对 OCEAN 的影响值（仅 user 消息有）",
    )
    created_at: Optional[str] = Field(default=None, description="创建时间 ISO 格式")


class MessageListResponse(BaseModel):
    """对话历史列表"""

    session_id: str
    messages: List[MessageItem]
    total: int


# ============================================================
# 通用错误响应
# ============================================================

class ErrorResponse(BaseModel):
    """统一错误响应"""

    detail: str = Field(..., description="错误描述")
    error_code: Optional[str] = Field(default=None, description="错误代码")
