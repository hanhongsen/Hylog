"""
API 核心路由

定义 Hylog 会话与对话相关的 5 个 HTTP 接口：
- POST   /api/sessions                       创建会话
- POST   /api/sessions/{session_id}/reply     提交回答
- GET    /api/sessions/{session_id}/state     查询进度
- GET    /api/sessions/{session_id}/result    查询结果
- GET    /api/sessions/{session_id}/messages  查询对话历史

设计说明：
- 每次 POST /reply 都通过 ConversationAgent.restore() 从数据库恢复状态，
  处理完后再 _persist_state() 持久化。这是 HTTP 无状态架构的标准做法。
- 创建会话时根据 USE_MOCK_AGENT 开关决定真实/Mock 模式。
- 回答长度校验由 Pydantic 在 schemas.py 中完成（1~100 字符），超长返回 422。
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.agent import ConversationAgent
from src.utils.llm import LLMError

from .schemas import (
    CreateSessionRequest,
    ReplyRequest,
    ConversationResponse,
    SessionStateResponse,
    MessageListResponse,
    MessageItem,
    MatchResultInfo,
    ProgressInfo,
)
from .deps import get_db, get_mock_flag, get_db_path, load_session_or_404

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["会话与对话"])


# ============================================================
# 创建会话
# ============================================================

@router.post("/sessions", response_model=ConversationResponse, summary="创建会话并开始对话")
def create_session(
    request: CreateSessionRequest,
    use_mock: bool = Depends(get_mock_flag),
    db_path: str = Depends(get_db_path),
):
    """
    创建一个新的测试会话，返回开场白和第一个问题。

    - 请求体可传 user_id（不传则使用临时假用户，认证上线前的过渡方案）
    - 根据 .env 的 USE_MOCK_AGENT 决定真实/Mock 模式
    """
    user_id = request.user_id or "anonymous-user"

    try:
        agent = ConversationAgent.create(
            user_id=user_id,
            use_mock=use_mock,
            db_path=db_path,
        )
    except RuntimeError as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {e}")

    try:
        response = agent.start()
    except Exception as e:
        logger.error(f"开始对话失败: {e}", exc_info=True)
        agent.close()
        raise HTTPException(status_code=500, detail=f"开始对话失败: {e}")

    return _coerce_response(response)


# ============================================================
# 提交回答
# ============================================================

@router.post(
    "/sessions/{session_id}/reply",
    response_model=ConversationResponse,
    summary="提交回答，推进对话",
)
def reply(
    session_id: str,
    request: ReplyRequest,
    db_path: str = Depends(get_db_path),
    db: Session = Depends(get_db),
):
    """
    提交用户回答，推进对话流程。

    - 回答长度限制 1~100 字符（超出返回 422 校验错误）
    - 每次调用都会从数据库恢复会话状态，处理完后再持久化
    - 返回下一个问题，或测试完成时返回匹配结果
    """
    # 先校验会话存在（restore 内部也会查，这里提前给一个清晰的 404）
    load_session_or_404(db, session_id)
    db.close()  # 校验用的 db 关掉，下面用 agent 自己的 db_session

    try:
        agent = ConversationAgent.restore(session_id=session_id, db_path=db_path)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
    except RuntimeError as e:
        logger.error(f"恢复会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"恢复会话失败: {e}")

    try:
        response = agent.reply(request.answer)
    except LLMError as e:
        # LLM 调用失败：理论上 reply 内部已做了 fallback，不应抛到这里；
        # 但为防止意外，统一返回 503 让前端提示稍后重试
        logger.error(f"LLM 调用失败: {e}")
        raise HTTPException(status_code=503, detail=f"AI 服务暂时不可用，请稍后重试: {e}")
    except Exception as e:
        logger.error(f"处理回答失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理回答失败: {e}")

    return _coerce_response(response)


# ============================================================
# 查询会话状态
# ============================================================

@router.get(
    "/sessions/{session_id}/state",
    response_model=SessionStateResponse,
    summary="查询会话进度和人格状态",
)
def get_state(
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    返回当前的人格状态和对话进度，供前端展示。
    不修改任何状态，纯查询。
    """
    record = load_session_or_404(db, session_id)

    # 优先从 state_json 读取（最完整）
    state_data = record.state_json or {}

    # AgentState 存的 ocean_vector 是 OCEANVector.to_dict() 结构
    # 需要从中提取五个分数（O/C/E/A/N）
    ocean = state_data.get("ocean_vector", {})
    if "openness" in ocean:
        personality_state = {
            "O": round(ocean.get("openness", 0.5), 2),
            "C": round(ocean.get("conscientiousness", 0.5), 2),
            "E": round(ocean.get("extraversion", 0.5), 2),
            "A": round(ocean.get("agreeableness", 0.5), 2),
            "N": round(ocean.get("neuroticism", 0.5), 2),
        }
    else:
        personality_state = {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5}

    # 计算维度覆盖率（从 11 维探索次数中统计 >0 的数量）
    # explore_count 是 dict，如 {'social_explore_count': 1, 'emotion_explore_count': 0, ...}
    dim11 = state_data.get("dim11_vector", {})
    explore_counts = dim11.get("explore_count", {})
    if isinstance(explore_counts, dict):
        explored = sum(1 for v in explore_counts.values() if isinstance(v, (int, float)) and v > 0)
    elif isinstance(explore_counts, list):
        explored = sum(1 for v in explore_counts if isinstance(v, (int, float)) and v > 0)
    else:
        explored = 0

    from src.agent.state import MIN_ROUNDS, MAX_ROUNDS

    progress = ProgressInfo(
        turn=record.round_count or 0,
        min_rounds=MIN_ROUNDS,
        max_rounds=MAX_ROUNDS,
        dimension_coverage=f"{explored}/11",
        converged=bool(state_data.get("converged")),
    )

    # 结果（如果已完成）
    result_info = None
    if state_data.get("result"):
        result_info = MatchResultInfo(**state_data["result"])

    return SessionStateResponse(
        session_id=session_id,
        personality_state=personality_state,
        progress=progress,
        is_finished=bool(state_data.get("is_finished")) or (record.status == "completed"),
        result=result_info,
    )


# ============================================================
# 查询匹配结果
# ============================================================

@router.get(
    "/sessions/{session_id}/result",
    response_model=MatchResultInfo,
    summary="查询匹配结果",
)
def get_result(
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    返回该会话的最终匹配结果。

    - 测试未完成时返回 409
    - 当前付费字段全部返回（is_paid_locked=False），后续加付费分层再裁剪
    """
    record = load_session_or_404(db, session_id)

    state_data = record.state_json or {}
    if not state_data.get("result"):
        raise HTTPException(
            status_code=409,
            detail="本次测试尚未完成，暂无匹配结果",
        )

    return MatchResultInfo(**state_data["result"])


# ============================================================
# 查询对话历史
# ============================================================

@router.get(
    "/sessions/{session_id}/messages",
    response_model=MessageListResponse,
    summary="查询对话历史",
)
def get_messages(
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    返回该会话的所有对话消息（用户回答 + AI 回复），按时间正序。
    """
    load_session_or_404(db, session_id)

    from src.data import Message

    messages = (
        db.query(Message)
        .filter_by(session_id=session_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    items = [
        MessageItem(
            message_id=m.message_id,
            role=m.role,
            content=m.content,
            module=m.module,
            ocean_delta=m.ocean_delta,
            created_at=m.created_at.isoformat() if m.created_at else None,
        )
        for m in messages
    ]

    return MessageListResponse(
        session_id=session_id,
        messages=items,
        total=len(items),
    )


# ============================================================
# 辅助函数：把 Agent 的 dict 响应转换/校验为响应模型
# ============================================================

def _coerce_response(response: dict) -> ConversationResponse:
    """
    把 ConversationAgent._build_response() 的 dict 转换为 Pydantic 响应模型

    主要是处理 progress 和 result 的嵌套结构校验。
    """
    progress = ProgressInfo(**response["progress"])

    result_info = None
    if response.get("result"):
        result_info = MatchResultInfo(**response["result"])

    return ConversationResponse(
        session_id=response["session_id"],
        question=response.get("question"),
        message=response.get("message"),
        personality_state=response["personality_state"],
        progress=progress,
        is_finished=response["is_finished"],
        forced_finish=response.get("forced_finish", False),
        result=result_info,
    )
