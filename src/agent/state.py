"""
Agent 状态定义

本文件定义 Agent 调度模块的核心状态数据结构 AgentState。
AgentState 是整个对话流程的"记忆"，贯穿一个会话的完整生命周期，
负责持有：
- 人格状态（OCEAN 向量、11 维向量）
- 对话历史
- 流程控制信息（当前维度、轮次、是否收敛、是否结束）
- 最终匹配结果

设计说明：
- AgentState 是普通 Python 类（非 dataclass），因为需要在运行时灵活更新字段，
  且部分字段为复杂对象（OCEANVector / Dimension11Vector / MatchResult）
- 提供 to_dict / from_dict 方法支持序列化，用于持久化到数据库或断点恢复
- 阈值常量定义为模块级常量，方便统一调整
"""

from typing import Dict, List, Optional, Any

from src.personality import OCEANVector, Dimension11Vector
from src.personality.model import DIMENSION11_NAMES
from src.matching import MatchResult


# ============================================================
# 阈值常量（按 README 默认值，可在此统一调整）
# ============================================================

# 收敛条件
MIN_ROUNDS = 15                      # 最小对话轮次（总探索次数）
MIN_EXPLORE_PER_DIMENSION = 2        # 每个维度最小探索次数
MAX_UNCERTAINTY = 0.3                # 最大允许的平均不确定性

# 对话上限（兜底，防止无限循环）
MAX_ROUNDS = 30

# OCEAN 匹配相似度展示参考值（仅用于结果展示，不做流程拦截）
OCEAN_SIMILARITY_REFERENCE = 0.85

# 开场白文案（轻松随和风格，后续可替换）
OPENING_MESSAGE = (
    "嗨，我是 Hylog～欢迎来到一场关于「认识自己」的对话。\n\n"
    "接下来我会问你一些问题，没有标准答案，跟着真实想法回答就好。"
    "聊完之后，我会帮你找到历史上和你最像的那个人。\n\n"
    "准备好了吗？我们开始吧 😊"
)


# ============================================================
# AgentState 状态类
# ============================================================

class AgentState:
    """
    Agent 会话状态

    贯穿一次完整对话流程，由 ConversationAgent 持有并在各节点间传递。

    核心字段：
        session_id: 会话唯一标识（UUID）
        user_id: 用户 ID
        ocean_vector: OCEAN 五维人格向量
        dim11_vector: 11 维问题维度向量（用于探索次数/不确定性跟踪）
        history: 对话历史（内存中保留全部，完整记录入数据库）
        turn_count: 有效对话轮次（无效回答不计数）
        current_dimension: 当前正在探索的维度 ID
        converged: 是否已收敛
        convergence_details: 最近一次收敛判断的详情
        result: 最终匹配结果
        is_finished: 是否已结束
        forced_finish: 是否因达到最大轮次而强制结束
    """

    def __init__(
        self,
        session_id: str,
        user_id: str = "anonymous",
        ocean_vector: Optional[OCEANVector] = None,
        dim11_vector: Optional[Dimension11Vector] = None,
        history: Optional[List[Dict]] = None,
        turn_count: int = 0,
        current_dimension: Optional[str] = None,
        converged: bool = False,
        convergence_details: Optional[Dict] = None,
        result: Optional[MatchResult] = None,
        is_finished: bool = False,
        forced_finish: bool = False,
        use_mock: bool = False,
        mock_ocean_signs: Optional[Dict[str, int]] = None,
        skipped_dimensions: Optional[Dict[str, Dict]] = None,
    ):
        # 身份
        self.session_id = session_id
        self.user_id = user_id

        # 人格状态（默认初始化为中等分数、完全不确定）
        self.ocean_vector = ocean_vector if ocean_vector is not None else OCEANVector()
        self.dim11_vector = dim11_vector if dim11_vector is not None else Dimension11Vector()

        # 对话历史
        # 每条格式：{"role": "user"/"assistant", "content": "...", "dimension": "..."}
        self.history: List[Dict] = history if history is not None else []

        # 流程控制
        self.turn_count = turn_count
        self.current_dimension = current_dimension
        self.converged = converged
        self.convergence_details = convergence_details
        self.is_finished = is_finished
        self.forced_finish = forced_finish

        # 运行模式（True=不调智谱，用合成数据；False=真实调智谱）
        # 用于 nodes.py 判断是否跳过 LLM 调用
        self.use_mock = use_mock

        # Mock 模式下每个 OCEAN 维度的演化方向签名（+1 / -1 / 0）
        # 仅 use_mock=True 时使用，保证跨 HTTP 请求稳定演化，画像不漂移
        # 例：{"O": 1, "C": -1, "E": 1, "A": -1, "N": 1}
        self.mock_ocean_signs: Dict[str, int] = mock_ocean_signs if mock_ocean_signs is not None else {}

        # 因用户"不舒服/拒绝"而被跳过的维度记录，用于后续柔和化重新探索。
        # 不放弃探索，只是换更轻松的问法再问一次。
        # 结构：{"intimacy": {"reason": "uncomfortable", "skipped_at_turn": 5}, ...}
        # 该维度被跳过后不会收到 delta，OCEAN 不确定性不降，会自然重新进入喂饭队列；
        # 重新选中时，generate_question 会读取此标记，加柔和化提示词。
        self.skipped_dimensions: Dict[str, Dict] = skipped_dimensions if skipped_dimensions is not None else {}

        # 结果
        self.result = result

    # ============================================================
    # 维度探索数据的便捷访问（从 dim11_vector 提取）
    # ============================================================

    def get_dimension_uncertainty(self) -> Dict[str, float]:
        """
        获取 11 个维度各自的不确定性（供维度选择策略使用）

        返回:
            {"social": 0.8, "emotion": 0.7, ...}
        """
        uncertainties = self.dim11_vector.to_uncertainty_vector()
        return dict(zip(DIMENSION11_NAMES, uncertainties))

    def get_exploration_counts(self) -> Dict[str, int]:
        """
        获取 11 个维度各自的探索次数（供维度选择策略使用）

        返回:
            {"social": 1, "emotion": 2, ...}
        """
        counts = self.dim11_vector.to_explore_count_vector()
        return dict(zip(DIMENSION11_NAMES, counts))

    def get_ocean_dict(self) -> Dict[str, float]:
        """
        获取当前 OCEAN 分数（供匹配、LLM 分析、展示使用）

        返回:
            {"O": 0.72, "C": 0.65, "E": 0.45, "A": 0.58, "N": 0.32}
        """
        o = self.ocean_vector
        return {
            "O": round(o.openness, 2),
            "C": round(o.conscientiousness, 2),
            "E": round(o.extraversion, 2),
            "A": round(o.agreeableness, 2),
            "N": round(o.neuroticism, 2),
        }

    def get_explored_dimension_count(self) -> int:
        """
        获取已被探索过（探索次数 > 0）的维度数量

        返回:
            已探索的维度数（0-11）
        """
        counts = self.dim11_vector.to_explore_count_vector()
        return sum(1 for c in counts if c > 0)

    # ============================================================
    # 序列化（用于持久化到数据库 / 断点恢复）
    # ============================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        将状态序列化为字典（可 JSON 化）

        返回:
            可序列化的状态字典
        """
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "ocean_vector": self.ocean_vector.to_dict(),
            "dim11_vector": self.dim11_vector.to_dict(),
            "history": self.history,
            "turn_count": self.turn_count,
            "current_dimension": self.current_dimension,
            "converged": self.converged,
            "convergence_details": self.convergence_details,
            "is_finished": self.is_finished,
            "forced_finish": self.forced_finish,
            "use_mock": self.use_mock,
            "mock_ocean_signs": self.mock_ocean_signs,
            "skipped_dimensions": self.skipped_dimensions,
            "result": self.result.to_dict(include_paid=True) if self.result else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """
        从字典反序列化状态（用于断点恢复）

        参数:
            data: to_dict() 产生的字典

        返回:
            AgentState 实例
        """
        # 反序列化向量
        ocean_vector = OCEANVector.from_dict(data["ocean_vector"])
        dim11_vector = Dimension11Vector.from_dict(data["dim11_vector"])

        # 反序列化结果（如果有）
        result = None
        if data.get("result"):
            result = _match_result_from_dict(data["result"])

        return cls(
            session_id=data["session_id"],
            user_id=data.get("user_id", "anonymous"),
            ocean_vector=ocean_vector,
            dim11_vector=dim11_vector,
            history=data.get("history", []),
            turn_count=data.get("turn_count", 0),
            current_dimension=data.get("current_dimension"),
            converged=data.get("converged", False),
            convergence_details=data.get("convergence_details"),
            is_finished=data.get("is_finished", False),
            forced_finish=data.get("forced_finish", False),
            use_mock=data.get("use_mock", False),
            mock_ocean_signs=data.get("mock_ocean_signs", {}),
            skipped_dimensions=data.get("skipped_dimensions", {}),
            result=result,
        )

    # ============================================================
    # 状态摘要（供前端展示）
    # ============================================================

    def get_summary(self) -> Dict[str, Any]:
        """
        生成状态摘要（供前端展示当前进度）

        返回:
            包含人格状态、进度等信息的字典
        """
        return {
            "session_id": self.session_id,
            "personality_state": self.get_ocean_dict(),
            "progress": {
                "turn": self.turn_count,
                "min_rounds": MIN_ROUNDS,
                "max_rounds": MAX_ROUNDS,
                "dimension_coverage": f"{self.get_explored_dimension_count()}/11",
                "converged": self.converged,
            },
            "is_finished": self.is_finished,
            # 开发阶段全开放付费字段（与 graph._build_response 保持一致）
            "result": self.result.to_dict(include_paid=True) if self.result else None,
        }

    def __repr__(self):
        return (
            f"<AgentState(session_id={self.session_id}, "
            f"turn={self.turn_count}, converged={self.converged}, "
            f"finished={self.is_finished})>"
        )


# ============================================================
# 辅助函数：MatchResult 反序列化
# ============================================================

def _match_result_from_dict(data: Dict[str, Any]) -> MatchResult:
    """
    从字典反序列化 MatchResult

    参数:
        data: MatchResult.to_dict() 产生的字典

    返回:
        MatchResult 实例
    """
    from src.matching.matcher import CharacterData, MatchResult as MR

    # 反序列化人物数据
    char_data = data.get("character", {})
    character = CharacterData(
        character_id=char_data.get("character_id", ""),
        name=char_data.get("name", ""),
        source=char_data.get("source", ""),
        era=char_data.get("era", ""),
        description=char_data.get("description", ""),
        ocean_vector=char_data.get("ocean_vector", {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5}),
        image_path=char_data.get("image_path", ""),
        tags=char_data.get("tags", []),
        quote=char_data.get("quote", ""),
        personality_keyword=char_data.get("personality_keyword", ""),
        classic_events=char_data.get("classic_events", ""),
        fun_facts=char_data.get("fun_facts", ""),
        advice=char_data.get("advice", ""),
        related_books=char_data.get("related_books", ""),
        match_count=char_data.get("match_count", 0),
    )

    return MR(
        character=character,
        similarity=data.get("similarity", 0.0),
        similarity_percent=data.get("similarity_percent", 0),
        heat_level=data.get("heat_level", "中等"),
        heat_percent=data.get("heat_percent", 50),
        is_paid_locked=data.get("is_paid_locked", True),
    )
