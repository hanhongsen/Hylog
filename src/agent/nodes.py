"""
Agent 流程节点

本文件定义对话流程中的各个节点函数，每个节点职责单一：
- 接收 AgentState（和必要参数）
- 执行该步骤的业务逻辑
- 返回执行结果（不直接修改 state，由 ConversationAgent 统一编排）

节点列表：
    1. start_node                - 开始对话，输出固定开场白
    2. select_dimension_node     - 选择下一个探索维度
    3. generate_question_node    - 生成问题
    4. process_answer_node       - 记录用户回答
    5. update_personality_node   - LLM 分析回答 + 更新人格
    6. check_convergence_node    - 收敛判断
    7. match_character_node      - 匹配人物（只用 OCEAN）
    8. build_result_node         - 构建最终结果

设计原则：
- 节点是纯函数，不持有状态，便于测试和复用
- LLM 调用失败时优雅降级（问题用备用问题、人格分析失败跳过本轮）
- 无效回答（skipped）不增加 turn_count，返回引导语
"""

import logging
from typing import Dict, List, Optional, Tuple, Any

from src.personality import PersonalityUpdater
from src.questions import (
    generate_question as _generate_question,
    select_next_dimension,
    get_dimension_by_id,
)
from src.questions.modules import get_all_dimension_ids
from src.matching import (
    CharacterData,
    MatchResult,
    get_best_match,
    create_match_result,
)
from src.utils.llm import analyze_personality

from .state import AgentState, OPENING_MESSAGE, MIN_ROUNDS, MIN_EXPLORE_PER_DIMENSION, MAX_UNCERTAINTY

logger = logging.getLogger(__name__)


# ============================================================
# Mock 人物数据（用于 Agent 开发测试，不依赖真实数据库）
# ============================================================

MOCK_CHARACTERS: List[CharacterData] = [
    CharacterData(
        character_id="mock-zhugeliang",
        name="诸葛亮",
        source="历史",
        era="三国时期",
        description="蜀汉丞相，杰出的政治家、军事家。以智慧、忠诚、谨慎著称，鞠躬尽瘁，死而后已。",
        ocean_vector={"O": 0.65, "C": 0.95, "E": 0.30, "A": 0.85, "N": 0.35},
        tags=["智慧谨慎", "鞠躬尽瘁", "运筹帷幄"],
        quote="非淡泊无以明志，非宁静无以致远。",
        personality_keyword="智慧谨慎型",
    ),
    CharacterData(
        character_id="mock-caocao",
        name="曹操",
        source="历史",
        era="三国时期",
        description="魏国奠基人，杰出的政治家、军事家、文学家。雄才大略，多疑善变，唯才是举。",
        ocean_vector={"O": 0.80, "C": 0.75, "E": 0.85, "A": 0.30, "N": 0.60},
        tags=["雄才大略", "多疑果敢", "文武双全"],
        quote="宁教我负天下人，休教天下人负我。",
        personality_keyword="雄才果敢型",
    ),
    CharacterData(
        character_id="mock-libai",
        name="李白",
        source="历史",
        era="唐朝",
        description="唐代伟大的浪漫主义诗人，被誉为「诗仙」。豪放不羁，自由洒脱，才华横溢。",
        ocean_vector={"O": 0.95, "C": 0.30, "E": 0.90, "A": 0.55, "N": 0.45},
        tags=["自由浪漫", "豪放不羁", "诗酒风流"],
        quote="天生我材必有用，千金散尽还复来。",
        personality_keyword="自由浪漫型",
    ),
    CharacterData(
        character_id="mock-lindaiyu",
        name="林黛玉",
        source="文学",
        era="",
        description="《红楼梦》女主角，才情出众、敏感多情。心思细腻，多愁善感，孤高自许。",
        ocean_vector={"O": 0.90, "C": 0.50, "E": 0.25, "A": 0.55, "N": 0.85},
        tags=["多愁善感", "才华横溢", "孤高敏感"],
        quote="花谢花飞花满天，红消香断有谁怜。",
        personality_keyword="敏感才情型",
    ),
    CharacterData(
        character_id="mock-sushi",
        name="苏轼",
        source="历史",
        era="宋朝",
        description="北宋文学家，豁达乐观，旷达超脱。历经坎坷依然热爱生活，诗词书画皆精。",
        ocean_vector={"O": 0.88, "C": 0.65, "E": 0.75, "A": 0.78, "N": 0.30},
        tags=["豁达乐观", "旷达超脱", "热爱生活"],
        quote="竹杖芒鞋轻胜马，谁怕？一蓑烟雨任平生。",
        personality_keyword="豁达乐观型",
    ),
]


# ============================================================
# 节点 1：开始对话
# ============================================================

def start_node(state: AgentState) -> str:
    """
    开始对话节点

    输出固定开场白，并将首维度固定设为 social（社交互动最适合破冰）。

    参数:
        state: 当前会话状态（会被设置 current_dimension）

    返回:
        开场白文本
    """
    # 首维度固定为 social
    state.current_dimension = "social"
    logger.info(f"[{state.session_id}] 会话开始，首维度: social")
    return OPENING_MESSAGE


# ============================================================
# 节点 2：选择下一个探索维度
# ============================================================

def select_dimension_node(state: AgentState) -> str:
    """
    选择下一个探索维度

    根据当前各维度的不确定性和探索次数，选择下一个最该探索的维度。
    策略（由 select_next_dimension 实现）：
      1. 优先探索不确定性最高的维度
      2. 其次探索次数不足的维度
      3. 最后随机选择

    参数:
        state: 当前会话状态

    返回:
        选定的维度 ID
    """
    dimension_uncertainty = state.get_dimension_uncertainty()
    exploration_counts = state.get_exploration_counts()

    next_dim = select_next_dimension(dimension_uncertainty, exploration_counts)
    state.current_dimension = next_dim

    dim = get_dimension_by_id(next_dim)
    logger.info(f"[{state.session_id}] 选定下一维度: {next_dim}({dim.name})")
    return next_dim


# ============================================================
# 节点 3：生成问题
# ============================================================

def generate_question_node(state: AgentState) -> str:
    """
    生成问题节点

    基于当前维度、对话历史、人格状态生成下一个问题。
    LLM 调用失败时自动 fallback 到该维度的备用问题。

    参数:
        state: 当前会话状态

    返回:
        问题文本
    """
    dimension_id = state.current_dimension

    # 构建历史（generate_question 内部会截取最近2轮）
    # history 格式要求 [{"question": "...", "answer": "..."}]
    history_for_generation = _build_history_for_question(state.history)

    # 当前 OCEAN 分数
    current_ocean = state.get_ocean_dict()

    try:
        result = _generate_question(
            dimension_id=dimension_id,
            history=history_for_generation,
            current_ocean=current_ocean,
        )
        question = result["question"]
        logger.info(f"[{state.session_id}] 问题生成成功(维度:{dimension_id})")
    except Exception as e:
        # 生成失败，使用该维度的备用问题
        logger.warning(f"[{state.session_id}] 问题生成失败({e})，使用备用问题")
        dim = get_dimension_by_id(dimension_id)
        question = dim.get_random_question()

    return question


def _build_history_for_question(history: List[Dict]) -> List[Dict]:
    """
    将 AgentState.history 转换为 generate_question 所需的历史格式

    AgentState.history 格式: [{"role": "user"/"assistant", "content": "...", "dimension": "..."}]
    generate_question 需要: [{"question": "...", "answer": "..."}]

    参数:
        history: AgentState 中的对话历史

    返回:
        generate_question 所需格式的历史列表
    """
    result = []
    i = 0
    while i < len(history) - 1:
        # 配对：assistant 的问题 + user 的回答
        current = history[i]
        nxt = history[i + 1]
        if current.get("role") == "assistant" and nxt.get("role") == "user":
            result.append({
                "question": current.get("content", ""),
                "answer": nxt.get("content", ""),
            })
            i += 2
        else:
            i += 1
    return result


# ============================================================
# 节点 4：记录用户回答
# ============================================================

def process_answer_node(state: AgentState, user_answer: str) -> None:
    """
    记录用户回答节点

    将用户回答追加到对话历史。
    注意：此节点不增加 turn_count，turn_count 在人格更新成功后才增加。

    参数:
        state: 当前会话状态
        user_answer: 用户的回答文本
    """
    state.history.append({
        "role": "user",
        "content": user_answer,
        "dimension": state.current_dimension,
    })


# ============================================================
# 节点 5：更新人格（核心节点）
# ============================================================

def update_personality_node(
    state: AgentState,
    user_answer: str,
    updater: PersonalityUpdater
) -> Dict[str, Any]:
    """
    更新人格节点

    流程：
    1. 调用 LLM 分析用户回答，得到 OCEAN 影响值（deltas）
    2. 检查是否为 skipped（无效回答）
       - 若 skipped：返回引导语，不更新人格，不增加 turn_count
       - 若有效：用 deltas 更新 OCEAN 和 11 维向量，turn_count + 1
    3. LLM 调用失败时：跳过本轮更新，不增加 turn_count，正常继续下一轮

    参数:
        state: 当前会话状态（会被更新 ocean_vector / dim11_vector）
        user_answer: 用户的回答文本
        updater: 人格更新器实例

    返回:
        更新结果字典：
        {
            "success": bool,           # 是否成功更新人格
            "skipped": bool,           # 是否因无效回答被跳过
            "guidance": Optional[str], # 跳过时的引导语
            "ocean_delta": Dict,       # 本次 OCEAN 变化量
        }
    """
    dimension = state.current_dimension
    current_ocean = state.get_ocean_dict()

    try:
        # 调用 LLM 分析
        analysis = analyze_personality(
            user_answer=user_answer,
            current_ocean=current_ocean,
            question_dimension=dimension,
        )
    except Exception as e:
        # LLM 调用失败（网络/API错误等），跳过本轮更新
        # llm 模块内部已有5次重试机制，到这里说明真的失败了
        logger.error(f"[{state.session_id}] 人格分析失败({e})，跳过本轮")
        return {
            "success": False,
            "skipped": False,
            "guidance": None,
            "ocean_delta": {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0},
            "error": str(e),
        }

    # 检查是否为无效回答
    if analysis.get("skipped"):
        guidance = analysis.get("guidance", "没关系，我们换个角度聊聊吧。")
        logger.info(f"[{state.session_id}] 回答被跳过({analysis.get('reason')})，不增加轮次")
        return {
            "success": False,
            "skipped": True,
            "guidance": guidance,
            "ocean_delta": {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0},
        }

    # 有效回答：计算 deltas 并更新人格
    ocean_delta = {
        dim: analysis.get(dim, 0.0)
        for dim in ["O", "C", "E", "A", "N"]
    }

    # 计算 11 维的变化量（取该维度映射的 OCEAN 维度 deltas 的平均值）
    from src.personality.model import DIMENSION11_TO_OCEAN_MAPPING
    mapped_dims = DIMENSION11_TO_OCEAN_MAPPING.get(dimension, [])
    if mapped_dims:
        dim11_delta = sum(ocean_delta.get(d, 0.0) for d in mapped_dims) / len(mapped_dims)
    else:
        dim11_delta = 0.0

    # 更新 OCEAN 和 11 维（就地修改）
    # update_ocean_from_dimension11 内部会按映射把 delta 分配到 OCEAN 各维
    updater.update_ocean_from_dimension11(
        ocean_vector=state.ocean_vector,
        dim11_vector=state.dim11_vector,
        dimension=dimension,
        delta=dim11_delta,
    )

    # 直接用 LLM 给出的 OCEAN deltas 覆盖更新一次
    # （因为 update_ocean_from_dimension11 会均分 delta，而 LLM 已给出更精准的判断）
    updater.update_ocean(state.ocean_vector, ocean_delta)

    # 有效回答，轮次 + 1
    state.turn_count += 1

    logger.info(
        f"[{state.session_id}] 人格更新成功(维度:{dimension}, 轮次:{state.turn_count}), "
        f"delta={ocean_delta}"
    )

    return {
        "success": True,
        "skipped": False,
        "guidance": None,
        "ocean_delta": ocean_delta,
    }


# ============================================================
# 节点 6：收敛判断
# ============================================================

def check_convergence_node(
    state: AgentState,
    updater: PersonalityUpdater
) -> Tuple[bool, Dict]:
    """
    收敛判断节点

    判断人格画像是否已收敛（信息量足够）。
    收敛需同时满足：
    1. 总探索次数 ≥ MIN_ROUNDS (15)
    2. 每个维度探索次数 ≥ MIN_EXPLORE_PER_DIMENSION (2)
    3. OCEAN 和 11 维的平均不确定性 < MAX_UNCERTAINTY (0.3)

    参数:
        state: 当前会话状态（会被更新 converged / convergence_details）
        updater: 人格更新器实例

    返回:
        (是否收敛, 详情字典)
    """
    converged, details = updater.check_convergence(
        ocean_vector=state.ocean_vector,
        dim11_vector=state.dim11_vector,
        min_rounds=MIN_ROUNDS,
        min_explore_per_dimension=MIN_EXPLORE_PER_DIMENSION,
        max_uncertainty=MAX_UNCERTAINTY,
    )

    state.converged = converged
    state.convergence_details = details

    logger.info(f"[{state.session_id}] 收敛判断: {converged}, 详情: {details['details']}")
    return converged, details


# ============================================================
# 节点 7：匹配人物（只用 OCEAN）
# ============================================================

def match_character_node(
    state: AgentState,
    characters: List[CharacterData]
) -> Optional[Tuple[CharacterData, float]]:
    """
    匹配人物节点

    用当前 OCEAN 分数与人物库进行余弦相似度匹配，返回最佳匹配。
    注意：匹配只用 OCEAN 5 维，不涉及 11 维数据。

    参数:
        state: 当前会话状态
        characters: 人物库列表

    返回:
        (最佳匹配人物, 相似度) 或 None（人物库为空）
    """
    user_ocean = state.get_ocean_dict()

    best = get_best_match(user_ocean, characters)

    if best is None:
        logger.warning(f"[{state.session_id}] 人物库为空，无法匹配")
        return None

    character, similarity = best
    logger.info(
        f"[{state.session_id}] 匹配结果: {character.name} "
        f"(相似度: {similarity:.4f})"
    )
    return best


# ============================================================
# 节点 8：构建最终结果
# ============================================================

def build_result_node(
    state: AgentState,
    character: CharacterData,
    similarity: float,
    all_characters: List[CharacterData],
    forced: bool = False
) -> MatchResult:
    """
    构建最终结果节点

    将匹配的人物封装为 MatchResult，并写入 state.result。

    参数:
        state: 当前会话状态（会被设置 result / is_finished）
        character: 匹配的人物
        similarity: 相似度
        all_characters: 完整人物库（用于计算热度等级）
        forced: 是否为强制结束（达到最大轮次）

    返回:
        MatchResult 实例
    """
    # 计算热度等级所需的数据
    total_characters = len(all_characters)
    all_match_counts = [c.match_count for c in all_characters]

    # 构建结果（开发阶段默认解锁全部内容 include_paid=True）
    result = create_match_result(
        character=character,
        similarity=similarity,
        total_characters=total_characters,
        all_match_counts=all_match_counts,
        include_paid=True,
    )

    state.result = result
    state.is_finished = True
    state.forced_finish = forced

    logger.info(
        f"[{state.session_id}] 结果构建完成: {character.name} "
        f"(相似度:{result.similarity_percent}%, 强制:{forced})"
    )
    return result
