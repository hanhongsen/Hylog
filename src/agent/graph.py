"""
ConversationAgent - 对话流程主控制器

本文件定义 ConversationAgent 类，作为 Agent 调度模块的核心，
负责编排 state.py（状态）和 nodes.py（节点）形成完整的对话流程。

核心职责：
1. 会话生命周期管理（创建/恢复/结束）
2. 对话流程编排（节点调用顺序、路由决策）
3. 数据持久化（Message / PersonalitySnapshot / Result 入库）
4. 提供统一的对外接口（start / reply / get_state_summary）

设计原则：
- Agent 持有一个 AgentState 实例，每次 reply 后持久化
- 路由决策（收敛后是否结束、是否强制结束）集中在此处
- Mock 模式（use_mock=True）不依赖数据库和真实人物库，便于独立测试
- 真实模式从数据库加载人物、持久化对话记录

使用示例：
    # 创建 Agent 并开始对话
    agent = ConversationAgent.create(use_mock=True)
    response = agent.start()

    # 多轮对话
    for _ in range(20):
        response = agent.reply("用户的回答")
        if response["is_finished"]:
            break

    # 获取结果
    result = agent.state.result
"""

import logging
import uuid
from typing import Dict, List, Optional, Any

from src.personality import PersonalityUpdater
from src.matching import CharacterData, MatchResult

from .state import AgentState, MAX_ROUNDS
from .nodes import (
    start_node,
    select_dimension_node,
    generate_question_node,
    process_answer_node,
    update_personality_node,
    check_convergence_node,
    match_character_node,
    build_result_node,
    MOCK_CHARACTERS,
)

logger = logging.getLogger(__name__)


# ============================================================
# 默认配置
# ============================================================

# 开发用 SQLite 数据库路径
DEFAULT_DB_PATH = "hylog.db"

# 匿名用户 ID（Mock 模式下自动创建的用户）
ANONYMOUS_USER_ID = "anonymous-user"


class ConversationAgent:
    """
    对话流程主控制器

    一个实例对应一个会话（session），持有该会话的完整状态。
    通过 start() 开始对话，reply() 处理用户回答并推进流程。

    属性:
        state: AgentState 会话状态
        updater: PersonalityUpdater 人格更新器
        use_mock: 是否使用 Mock 模式（不依赖数据库）
        characters: 人物库列表
    """

    def __init__(
        self,
        state: AgentState,
        characters: List[CharacterData],
        use_mock: bool = False,
        db_session=None,
    ):
        """
        初始化 Agent（通常通过 create() 工厂方法创建，而非直接构造）

        参数:
            state: 会话状态
            characters: 人物库列表
            use_mock: 是否 Mock 模式
            db_session: 数据库会话（真实模式用于持久化，Mock 模式为 None）
        """
        self.state = state
        self.characters = characters
        self.use_mock = use_mock
        self.db_session = db_session
        self.updater = PersonalityUpdater()

    # ============================================================
    # 工厂方法
    # ============================================================

    @classmethod
    def create(
        cls,
        user_id: str = ANONYMOUS_USER_ID,
        use_mock: bool = False,
        db_path: str = DEFAULT_DB_PATH,
    ) -> "ConversationAgent":
        """
        创建一个新的会话 Agent

        参数:
            user_id: 用户 ID（Mock 模式下使用匿名用户）
            use_mock: 是否使用 Mock 模式（推荐开发阶段使用）
            db_path: 数据库路径（仅真实模式使用）

        返回:
            新的 ConversationAgent 实例
        """
        session_id = str(uuid.uuid4())

        if use_mock:
            # Mock 模式：不连数据库，使用内置人物
            state = AgentState(session_id=session_id, user_id=user_id)
            return cls(
                state=state,
                characters=MOCK_CHARACTERS,
                use_mock=True,
                db_session=None,
            )

        # 真实模式：连接数据库
        # 优先复用全局单例（FastAPI 等 Web 场景），避免每次请求都新建 engine
        from src.data import (
            init_database, init_global_database, get_session_local,
            Session as SessionModel, User
        )

        db_url = f"sqlite:///{db_path}"
        try:
            SessionLocal = get_session_local()
        except RuntimeError:
            # 全局未初始化（脚本场景），用模块级单例初始化一次
            _, SessionLocal = init_global_database(db_url)

        db = SessionLocal()

        try:
            # 确保用户存在（Session 表的 user_id 是 NOT NULL 外键）
            user = db.query(User).filter_by(user_id=user_id).first()
            if user is None:
                user = User(
                    user_id=user_id,
                    nickname="匿名用户" if user_id == ANONYMOUS_USER_ID else user_id,
                )
                db.add(user)
                db.commit()

            # 创建会话记录
            session_record = SessionModel(
                session_id=session_id,
                user_id=user_id,
                status="in_progress",
                round_count=0,
                current_module="social",
            )
            db.add(session_record)
            db.commit()

            # 初始化状态快照并写入 state_json（start() 之前是初始状态）
            initial_state = AgentState(session_id=session_id, user_id=user_id)
            session_record.state_json = initial_state.to_dict()
            db.commit()

            # 从数据库加载人物库
            from src.data import Character
            char_records = db.query(Character).filter(Character.is_active == True).all()
            characters = [
                CharacterData(
                    character_id=c.character_id,
                    name=c.name,
                    source=c.source,
                    era=c.era or "",
                    description=c.description or "",
                    ocean_vector=c.ocean_vector or {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5},
                    image_path=c.image_path or "",
                    tags=c.tags or [],
                    quote=c.quote or "",
                    personality_keyword=c.personality_keyword or "",
                    classic_events=c.classic_events or "",
                    fun_facts=c.fun_facts or "",
                    advice=c.advice or "",
                    related_books=c.related_books or "",
                    match_count=c.match_count or 0,
                    is_active=c.is_active,
                )
                for c in char_records
            ]

            if not characters:
                logger.warning(
                    f"数据库人物库为空！请先运行 scripts/build_character_db.py 构建人物库。"
                )

        except Exception as e:
            db.close()
            raise RuntimeError(f"创建会话失败: {e}")

        state = AgentState(session_id=session_id, user_id=user_id)
        agent = cls(
            state=state,
            characters=characters,
            use_mock=False,
            db_session=db,
        )
        return agent

    @classmethod
    def restore(
        cls,
        session_id: str,
        db_path: str = DEFAULT_DB_PATH,
    ) -> "ConversationAgent":
        """
        从数据库恢复一个已存在的会话（用于 HTTP API 每次请求时重建状态）

        流程：
        1. 从 Session 表读取 state_json 字段
        2. 用 AgentState.from_dict() 反序列化
        3. 加载人物库
        4. 构造 ConversationAgent 实例

        参数:
            session_id: 要恢复的会话 ID
            db_path: 数据库路径

        返回:
            恢复后的 ConversationAgent 实例

        异常:
            ValueError: 会话不存在
            RuntimeError: 会话状态无法恢复
        """
        from src.data import (
            get_session_local, init_global_database,
            Session as SessionModel, Character,
        )

        db_url = f"sqlite:///{db_path}"
        try:
            SessionLocal = get_session_local()
        except RuntimeError:
            _, SessionLocal = init_global_database(db_url)

        db = SessionLocal()

        try:
            # 读取会话记录
            session_record = (
                db.query(SessionModel)
                .filter_by(session_id=session_id)
                .first()
            )
            if session_record is None:
                db.close()
                raise ValueError(f"会话不存在: {session_id}")

            # 反序列化状态
            if not session_record.state_json:
                db.close()
                raise RuntimeError(f"会话状态快照为空，无法恢复: {session_id}")

            state = AgentState.from_dict(session_record.state_json)

            # 加载人物库（与 create() 保持一致）
            char_records = db.query(Character).filter(Character.is_active == True).all()
            characters = [
                CharacterData(
                    character_id=c.character_id,
                    name=c.name,
                    source=c.source,
                    era=c.era or "",
                    description=c.description or "",
                    ocean_vector=c.ocean_vector or {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5},
                    image_path=c.image_path or "",
                    tags=c.tags or [],
                    quote=c.quote or "",
                    personality_keyword=c.personality_keyword or "",
                    classic_events=c.classic_events or "",
                    fun_facts=c.fun_facts or "",
                    advice=c.advice or "",
                    related_books=c.related_books or "",
                    match_count=c.match_count or 0,
                    is_active=c.is_active,
                )
                for c in char_records
            ]

        except (ValueError, RuntimeError):
            raise
        except Exception as e:
            db.close()
            raise RuntimeError(f"恢复会话失败: {e}")

        return cls(
            state=state,
            characters=characters,
            use_mock=False,
            db_session=db,
        )

    # ============================================================
    # 开始对话
    # ============================================================

    def start(self) -> Dict[str, Any]:
        """
        开始对话，输出开场白和第一个问题

        流程：
        1. start_node 输出固定开场白
        2. 生成第一个问题（维度固定为 social）

        返回:
            响应字典：
            {
                "session_id": "...",
                "question": "开场白 + 第一个问题",
                "personality_state": {...},
                "progress": {...},
                "is_finished": False,
                "result": None,
            }
        """
        # 输出开场白
        opening = start_node(self.state)

        # 生成第一个问题（current_dimension 已被 start_node 设为 social）
        first_question = generate_question_node(self.state)

        # 组合开场白和第一个问题
        full_message = f"{opening}\n\n---\n\n{first_question}"

        # 记录到历史
        self.state.history.append({
            "role": "assistant",
            "content": full_message,
            "dimension": self.state.current_dimension,
        })

        # 持久化开场白消息（真实模式）
        self._persist_message("assistant", full_message, self.state.current_dimension)

        # 持久化完整状态快照（供下次请求恢复）
        self._persist_state()

        logger.info(f"[{self.state.session_id}] 对话开始")
        return self._build_response(full_message)

    # ============================================================
    # 处理用户回答（核心方法）
    # ============================================================

    def reply(self, user_answer: str) -> Dict[str, Any]:
        """
        处理用户回答，推进对话流程

        完整流程：
        1. 记录用户回答（process_answer）
        2. LLM 分析 + 更新人格（update_personality）
           - 若 skipped：返回引导语，不增加 turn_count，继续生成下一问题
           - 若 LLM 失败：跳过本轮，继续生成下一问题
        3. 收敛判断（check_convergence）
        4. 路由决策：
           - 已收敛 → 匹配人物 → 输出结果
           - 未收敛 且 turn < MAX_ROUNDS → 选维度 + 生成问题 → 返回问题
           - 达 MAX_ROUNDS → 强制匹配人物 → 输出结果

        参数:
            user_answer: 用户的回答文本

        返回:
            响应字典（见 _build_response）
        """
        # 已结束的会话直接返回结果
        if self.state.is_finished:
            return self._build_response(None, already_finished=True)

        # ① 记录用户回答
        process_answer_node(self.state, user_answer)
        self._persist_message("user", user_answer, self.state.current_dimension)

        # ② 更新人格
        update_result = update_personality_node(
            self.state, user_answer, self.updater
        )

        # 持久化人格快照（有效更新后）
        if update_result["success"]:
            self._persist_snapshot()

        # 持久化 ocean_delta 到用户消息（真实模式）
        if update_result.get("ocean_delta") and not self.use_mock:
            self._update_message_delta(user_answer, update_result["ocean_delta"])

        # 无效回答被跳过：返回引导语 + 重新生成问题（同一维度）
        if update_result["skipped"]:
            guidance = update_result["guidance"]
            next_question = generate_question_node(self.state)
            full_message = f"{guidance}\n\n{next_question}"

            self.state.history.append({
                "role": "assistant",
                "content": full_message,
                "dimension": self.state.current_dimension,
            })
            self._persist_message("assistant", full_message, self.state.current_dimension)
            self._persist_state()
            return self._build_response(full_message)

        # LLM 调用失败：跳过本轮，继续生成下一问题
        if not update_result["success"]:
            select_dimension_node(self.state)
            next_question = generate_question_node(self.state)

            self.state.history.append({
                "role": "assistant",
                "content": next_question,
                "dimension": self.state.current_dimension,
            })
            self._persist_message("assistant", next_question, self.state.current_dimension)
            self._persist_state()
            return self._build_response(next_question)

        # ③ 收敛判断
        converged, details = check_convergence_node(self.state, self.updater)

        # ④ 路由决策
        # 情况 A：已收敛 → 匹配人物并输出结果
        if converged:
            return self._finish()

        # 情况 B：达到最大轮次 → 强制匹配人物并输出结果
        if self.state.turn_count >= MAX_ROUNDS:
            logger.info(f"[{self.state.session_id}] 达到最大轮次({MAX_ROUNDS})，强制输出结果")
            return self._finish(forced=True)

        # 情况 C：未收敛 → 选维度 + 生成下一问题
        select_dimension_node(self.state)
        next_question = generate_question_node(self.state)

        self.state.history.append({
            "role": "assistant",
            "content": next_question,
            "dimension": self.state.current_dimension,
        })
        self._persist_message("assistant", next_question, self.state.current_dimension)

        # 更新会话轮次（真实模式）
        self._update_session_record()

        # 持久化完整状态快照（供下次请求恢复）
        self._persist_state()

        return self._build_response(next_question)

    # ============================================================
    # 结束流程（匹配 + 输出结果）
    # ============================================================

    def _finish(self, forced: bool = False) -> Dict[str, Any]:
        """
        匹配人物并构建最终结果

        参数:
            forced: 是否为强制结束（达到最大轮次）

        返回:
            包含最终结果的响应字典
        """
        # 匹配人物
        best = match_character_node(self.state, self.characters)

        if best is None:
            # 人物库为空（不应发生，但做防御）
            error_msg = "抱歉，人物库暂时为空，无法完成匹配。"
            self.state.is_finished = True
            self.state.forced_finish = forced
            self._persist_state()
            return self._build_response(error_msg)

        character, similarity = best

        # 构建结果
        result = build_result_node(
            self.state, character, similarity, self.characters, forced=forced
        )

        # 持久化结果
        self._persist_result(result)

        # 更新人物匹配次数
        self._increment_character_match_count(character.character_id)

        # 更新会话状态为已完成
        self._complete_session_record()

        # 构建结束消息
        similarity_pct = result.similarity_percent
        finish_msg = (
            f"经过 {self.state.turn_count} 轮对话，我对你的人格画像已经比较清晰了。\n\n"
            f"和你最像的人物是：**{character.name}**（{character.source}"
            + (f"·{character.era}" if character.era else "")
            + f"），相似度 {similarity_pct}%。\n\n"
            f"{character.description}"
        )

        # 持久化完整状态快照（含最终结果）
        self._persist_state()

        return self._build_response(finish_msg)

    # ============================================================
    # 响应构建
    # ============================================================

    def _build_response(
        self,
        message: Optional[str],
        already_finished: bool = False
    ) -> Dict[str, Any]:
        """
        构建标准响应字典

        参数:
            message: 返回给用户的消息（问题/结果）
            already_finished: 会话是否已结束（用于 reply 到已结束会话的情况）

        返回:
            标准响应字典
        """
        summary = self.state.get_summary()
        return {
            "session_id": self.state.session_id,
            "question": message if not already_finished else None,
            "message": "本次测试已完成" if already_finished else message,
            "personality_state": summary["personality_state"],
            "progress": summary["progress"],
            "is_finished": self.state.is_finished,
            "forced_finish": self.state.forced_finish,
            "result": self.state.result.to_dict(include_paid=False) if self.state.result else None,
        }

    # ============================================================
    # 获取状态摘要（供前端展示）
    # ============================================================

    def get_state_summary(self) -> Dict[str, Any]:
        """
        获取当前会话状态摘要

        返回:
            状态摘要字典
        """
        return self.state.get_summary()

    # ============================================================
    # 持久化方法（Mock 模式下为空操作）
    # ============================================================

    def _persist_state(self):
        """
        持久化完整 AgentState 到 Session.state_json

        这是 API 状态恢复的核心：每次 start/reply/_finish 后调用，
        将当前的 OCEAN 向量、不确定性、对话历史、收敛详情等完整状态写入数据库，
        下一次 HTTP 请求时通过 restore() + AgentState.from_dict() 恢复。

        与 Message/PersonalitySnapshot 表的区别：
        - state_json：完整状态快照，用于运行时恢复（高频读写）
        - Message 表：对话历史归档（用于前端历史展示）
        - PersonalitySnapshot 表：人格演化轨迹（用于可视化）
        """
        if self.use_mock or self.db_session is None:
            return
        try:
            from src.data import Session as SessionModel
            session = (
                self.db_session.query(SessionModel)
                .filter_by(session_id=self.state.session_id)
                .first()
            )
            if session:
                session.state_json = self.state.to_dict()
                # 同步更新轮次和当前维度（保持冗余字段一致）
                session.round_count = self.state.turn_count
                session.current_module = self.state.current_dimension
                self.db_session.commit()
        except Exception as e:
            logger.error(f"持久化状态失败: {e}")
            self.db_session.rollback()

    def _persist_message(self, role: str, content: str, dimension: Optional[str] = None):
        """持久化对话消息到数据库"""
        if self.use_mock or self.db_session is None:
            return
        try:
            from src.data import Message
            msg = Message(
                message_id=str(uuid.uuid4()),
                session_id=self.state.session_id,
                role=role,
                content=content,
                module=dimension,
            )
            self.db_session.add(msg)
            self.db_session.commit()
        except Exception as e:
            logger.error(f"持久化消息失败: {e}")
            self.db_session.rollback()

    def _persist_snapshot(self):
        """持久化人格快照到数据库"""
        if self.use_mock or self.db_session is None:
            return
        try:
            from src.data import PersonalitySnapshot
            o = self.state.ocean_vector
            d = self.state.dim11_vector
            snapshot = PersonalitySnapshot(
                snapshot_id=str(uuid.uuid4()),
                session_id=self.state.session_id,
                round=self.state.turn_count,
                ocean_vector={"O": o.openness, "C": o.conscientiousness, "E": o.extraversion,
                              "A": o.agreeableness, "N": o.neuroticism},
                ocean_uncertainty={"openness": o.openness_uncertainty,
                                   "conscientiousness": o.conscientiousness_uncertainty,
                                   "extraversion": o.extraversion_uncertainty,
                                   "agreeableness": o.agreeableness_uncertainty,
                                   "neuroticism": o.neuroticism_uncertainty},
                dim11_vector=d.to_dict()["scores"],
                dim11_uncertainty=d.to_dict()["uncertainty"],
                dim11_explore_count=d.to_dict()["explore_count"],
            )
            self.db_session.add(snapshot)
            self.db_session.commit()
        except Exception as e:
            logger.error(f"持久化快照失败: {e}")
            self.db_session.rollback()

    def _update_message_delta(self, user_answer: str, ocean_delta: Dict[str, float]):
        """更新最近一条用户消息的 ocean_delta"""
        if self.use_mock or self.db_session is None:
            return
        try:
            from src.data import Message
            # 找到最近一条该回答的 user 消息
            msg = (
                self.db_session.query(Message)
                .filter_by(session_id=self.state.session_id, role="user", content=user_answer)
                .order_by(Message.created_at.desc())
                .first()
            )
            if msg:
                msg.ocean_delta = ocean_delta
                self.db_session.commit()
        except Exception as e:
            logger.error(f"更新消息delta失败: {e}")
            self.db_session.rollback()

    def _persist_result(self, result: MatchResult):
        """持久化最终结果到数据库"""
        if self.use_mock or self.db_session is None:
            return
        try:
            from src.data import Result
            result_record = Result(
                result_id=str(uuid.uuid4()),
                session_id=self.state.session_id,
                user_id=self.state.user_id,
                final_ocean=self.state.get_ocean_dict(),
                final_dim11=self.state.dim11_vector.to_dict()["scores"],
                matched_character_id=result.character.character_id,
                matched_character_name=result.character.name,
                matched_character_source=result.character.source,
                matched_similarity=result.similarity,
            )
            self.db_session.add(result_record)
            self.db_session.commit()
        except Exception as e:
            logger.error(f"持久化结果失败: {e}")
            self.db_session.rollback()

    def _increment_character_match_count(self, character_id: str):
        """增加人物的匹配次数（用于热度计算）"""
        if self.use_mock or self.db_session is None:
            return
        try:
            from src.data import Character
            char = self.db_session.query(Character).filter_by(character_id=character_id).first()
            if char:
                char.match_count = (char.match_count or 0) + 1
                self.db_session.commit()
        except Exception as e:
            logger.error(f"更新人物匹配次数失败: {e}")
            self.db_session.rollback()

    def _update_session_record(self):
        """更新会话表的轮次和当前维度"""
        if self.use_mock or self.db_session is None:
            return
        try:
            from src.data import Session as SessionModel
            session = self.db_session.query(SessionModel).filter_by(
                session_id=self.state.session_id
            ).first()
            if session:
                session.round_count = self.state.turn_count
                session.current_module = self.state.current_dimension
                self.db_session.commit()
        except Exception as e:
            logger.error(f"更新会话记录失败: {e}")
            self.db_session.rollback()

    def _complete_session_record(self):
        """标记会话为已完成"""
        if self.use_mock or self.db_session is None:
            return
        try:
            from datetime import datetime
            from src.data import Session as SessionModel
            session = self.db_session.query(SessionModel).filter_by(
                session_id=self.state.session_id
            ).first()
            if session:
                session.status = "completed"
                session.round_count = self.state.turn_count
                session.ended_at = datetime.now()
                self.db_session.commit()
        except Exception as e:
            logger.error(f"完成会话记录失败: {e}")
            self.db_session.rollback()

    # ============================================================
    # 资源清理
    # ============================================================

    def close(self):
        """关闭数据库连接"""
        if self.db_session is not None:
            self.db_session.close()
            self.db_session = None

    def __del__(self):
        """析构时自动关闭数据库连接"""
        try:
            self.close()
        except Exception:
            pass
