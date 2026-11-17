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
    # ---------- 先秦 ----------
    CharacterData(
        character_id="mock-kongzi",
        name="孔子",
        source="历史",
        era="春秋",
        description="儒家学派创始人，伟大的思想家、教育家。仁爱礼义，学而不厌，诲人不倦，周游列国推行其道。",
        ocean_vector={"O": 0.85, "C": 0.90, "E": 0.55, "A": 0.88, "N": 0.30},
        tags=["仁爱礼义", "诲人不倦", "中庸之道"],
        quote="己所不欲，勿施于人。",
        personality_keyword="仁厚睿智型",
    ),
    CharacterData(
        character_id="mock-laozi",
        name="老子",
        source="历史",
        era="春秋",
        description="道家学派创始人，深邃的哲学家。主张道法自然、无为而治，思想玄远幽深，影响深远。",
        ocean_vector={"O": 0.92, "C": 0.55, "E": 0.25, "A": 0.70, "N": 0.20},
        tags=["道法自然", "清静无为", "玄远深邃"],
        quote="上善若水，水善利万物而不争。",
        personality_keyword="玄远淡泊型",
    ),
    CharacterData(
        character_id="mock-zhuangzi",
        name="庄子",
        source="历史",
        era="战国",
        description="道家代表人物，浪漫主义哲学家。想象力奇绝，主张逍遥自在、齐物我一生死，超脱世俗。",
        ocean_vector={"O": 0.95, "C": 0.35, "E": 0.50, "A": 0.65, "N": 0.25},
        tags=["逍遥超脱", "奇思妙想", "齐物逍遥"],
        quote="天地与我并生，万物与我为一。",
        personality_keyword="逍遥超脱型",
    ),
    CharacterData(
        character_id="mock-quyuan",
        name="屈原",
        source="历史",
        era="战国",
        description="楚国诗人、政治家，浪漫主义文学奠基人。忠贞爱国，孤高洁白，因理想破灭投江明志。",
        ocean_vector={"O": 0.90, "C": 0.75, "E": 0.35, "A": 0.60, "N": 0.80},
        tags=["忠贞孤高", "浪漫忧愤", "九死不悔"],
        quote="路漫漫其修远兮，吾将上下而求索。",
        personality_keyword="孤高忧愤型",
    ),
    CharacterData(
        character_id="mock-sunwu",
        name="孙武",
        source="历史",
        era="春秋",
        description="兵家至圣，《孙子兵法》作者。深谙谋略，知己知彼，以慎战全胜为上，影响后世兵学。",
        ocean_vector={"O": 0.80, "C": 0.88, "E": 0.30, "A": 0.50, "N": 0.30},
        tags=["运筹帷幄", "知己知彼", "慎战全胜"],
        quote="知己知彼，百战不殆。",
        personality_keyword="深沉谋略型",
    ),
    # ---------- 秦汉 ----------
    CharacterData(
        character_id="mock-qinshihuang",
        name="秦始皇",
        source="历史",
        era="秦朝",
        description="中国首位皇帝，统一六国。雄才大略，开创中央集权，又因暴政苛法、焚书坑儒而饱受争议。",
        ocean_vector={"O": 0.70, "C": 0.85, "E": 0.80, "A": 0.20, "N": 0.65},
        tags=["雄才大略", "果决霸道", "千古一帝"],
        quote="朕为始皇帝，后世以计数。",
        personality_keyword="雄才霸道型",
    ),
    CharacterData(
        character_id="mock-xiangyu",
        name="项羽",
        source="历史",
        era="秦朝",
        description="西楚霸王，盖世武将。力拔山兮气盖世，勇猛无双却刚愎自用，终因妇人之仁与失谋而败亡乌江。",
        ocean_vector={"O": 0.55, "C": 0.40, "E": 0.90, "A": 0.35, "N": 0.70},
        tags=["盖世勇武", "刚愎自用", "重情重义"],
        quote="力拔山兮气盖世，时不利兮骓不逝。",
        personality_keyword="勇武刚愎型",
    ),
    CharacterData(
        character_id="mock-liubang",
        name="刘邦",
        source="历史",
        era="汉朝",
        description="汉高祖，汉朝开国皇帝。出身平民，豁达大度，知人善任，能屈能伸，终成帝业。",
        ocean_vector={"O": 0.65, "C": 0.60, "E": 0.85, "A": 0.55, "N": 0.40},
        tags=["豁达知人", "能屈能伸", "从谏如流"],
        quote="夫运筹策帷帐之中，决胜于千里之外，吾不如子房。",
        personality_keyword="豁达知人型",
    ),
    CharacterData(
        character_id="mock-zhangliang",
        name="张良",
        source="历史",
        era="汉朝",
        description="汉初三杰之一，杰出谋臣。运筹帷幄，深谋远虑，功成身退，淡泊名利，智慧超群。",
        ocean_vector={"O": 0.85, "C": 0.82, "E": 0.35, "A": 0.72, "N": 0.35},
        tags=["运筹帷幄", "功成身退", "深谋远虑"],
        quote="运筹帷幄之中，决胜千里之外。",
        personality_keyword="深沉智略型",
    ),
    CharacterData(
        character_id="mock-simaqian",
        name="司马迁",
        source="历史",
        era="汉朝",
        description="《史记》作者，伟大的史学家、文学家。忍辱负重，发愤著书，究天人之际，通古今之变。",
        ocean_vector={"O": 0.92, "C": 0.90, "E": 0.30, "A": 0.70, "N": 0.60},
        tags=["忍辱发愤", "究天人之际", "史家绝唱"],
        quote="人固有一死，或重于泰山，或轻于鸿毛。",
        personality_keyword="坚韧深察型",
    ),
    # ---------- 三国两晋 ----------
    CharacterData(
        character_id="mock-zhugeliang",
        name="诸葛亮",
        source="历史",
        era="三国",
        description="蜀汉丞相，杰出的政治家、军事家。以智慧、忠诚、谨慎著称，鞠躬尽瘁，死而后已。",
        ocean_vector={"O": 0.85, "C": 0.95, "E": 0.35, "A": 0.85, "N": 0.40},
        tags=["智慧谨慎", "鞠躬尽瘁", "运筹帷幄"],
        quote="非淡泊无以明志，非宁静无以致远。",
        personality_keyword="智慧谨慎型",
    ),
    CharacterData(
        character_id="mock-caocao",
        name="曹操",
        source="历史",
        era="三国",
        description="魏国奠基人，杰出的政治家、军事家、文学家。雄才大略，多疑善变，唯才是举。",
        ocean_vector={"O": 0.85, "C": 0.78, "E": 0.88, "A": 0.32, "N": 0.60},
        tags=["雄才大略", "多疑果敢", "文武双全"],
        quote="宁教我负天下人，休教天下人负我。",
        personality_keyword="雄才果敢型",
    ),
    CharacterData(
        character_id="mock-jikang",
        name="嵇康",
        source="历史",
        era="魏晋",
        description="竹林七贤之一，魏晋名士代表。孤高傲世，崇尚自然，拒绝仕途，因不与合作而被害。",
        ocean_vector={"O": 0.90, "C": 0.55, "E": 0.45, "A": 0.50, "N": 0.55},
        tags=["孤高傲世", "越名教任自然", "竹林风骨"],
        quote="非汤武而薄周孔，越名教而任自然。",
        personality_keyword="孤高傲世型",
    ),
    CharacterData(
        character_id="mock-taoyuanming",
        name="陶渊明",
        source="历史",
        era="晋朝",
        description="田园诗派鼻祖。不为五斗米折腰，归隐田园，恬淡自然，成为后世隐逸文化的象征。",
        ocean_vector={"O": 0.88, "C": 0.50, "E": 0.30, "A": 0.75, "N": 0.30},
        tags=["归隐田园", "恬淡自然", "不为五斗米折腰"],
        quote="采菊东篱下，悠然见南山。",
        personality_keyword="恬淡隐逸型",
    ),
    # ---------- 隋唐 ----------
    CharacterData(
        character_id="mock-tangtaizong",
        name="唐太宗",
        source="历史",
        era="唐朝",
        description="大唐盛世的开创者，贞观之治的明君。从谏如流，知人善任，文治武功兼备，开创大唐盛世。",
        ocean_vector={"O": 0.80, "C": 0.85, "E": 0.82, "A": 0.65, "N": 0.35},
        tags=["从谏如流", "贞观之治", "文治武功"],
        quote="以铜为镜，可以正衣冠；以史为镜，可以知兴替。",
        personality_keyword="明达大度型",
    ),
    CharacterData(
        character_id="mock-wuzetian",
        name="武则天",
        source="历史",
        era="唐朝",
        description="中国唯一的女皇帝。果决铁腕，知人善任，开创武周，功过难评，一代女皇气魄非凡。",
        ocean_vector={"O": 0.85, "C": 0.88, "E": 0.80, "A": 0.35, "N": 0.55},
        tags=["铁腕果决", "知人善任", "千古女皇"],
        quote="明堂坐天子，月匣鉴朝臣。",
        personality_keyword="铁腕果决型",
    ),
    CharacterData(
        character_id="mock-libai",
        name="李白",
        source="历史",
        era="唐朝",
        description="唐代伟大的浪漫主义诗人，被誉为「诗仙」。豪放不羁，自由洒脱，才华横溢。",
        ocean_vector={"O": 0.95, "C": 0.35, "E": 0.92, "A": 0.55, "N": 0.40},
        tags=["自由浪漫", "豪放不羁", "诗酒风流"],
        quote="天生我材必有用，千金散尽还复来。",
        personality_keyword="自由浪漫型",
    ),
    CharacterData(
        character_id="mock-dufu",
        name="杜甫",
        source="历史",
        era="唐朝",
        description="伟大的现实主义诗人，被誉为「诗圣」。忧国忧民，沉郁顿挫，笔下尽是苍生疾苦。",
        ocean_vector={"O": 0.88, "C": 0.82, "E": 0.35, "A": 0.80, "N": 0.75},
        tags=["忧国忧民", "沉郁顿挫", "诗史圣心"],
        quote="安得广厦千万间，大庇天下寒士俱欢颜。",
        personality_keyword="忧世悲悯型",
    ),
    # ---------- 宋朝 ----------
    CharacterData(
        character_id="mock-sushi",
        name="苏轼",
        source="历史",
        era="宋朝",
        description="北宋文学家，豁达乐观，旷达超脱。历经坎坷依然热爱生活，诗词书画皆精。",
        ocean_vector={"O": 0.92, "C": 0.65, "E": 0.78, "A": 0.78, "N": 0.30},
        tags=["豁达乐观", "旷达超脱", "热爱生活"],
        quote="竹杖芒鞋轻胜马，谁怕？一蓑烟雨任平生。",
        personality_keyword="豁达乐观型",
    ),
    CharacterData(
        character_id="mock-liqingzhao",
        name="李清照",
        source="历史",
        era="宋朝",
        description="宋代婉约派词宗，才华横溢的女词人。早年明媚，晚岁凄婉，词作情真意切，千古第一才女。",
        ocean_vector={"O": 0.90, "C": 0.70, "E": 0.40, "A": 0.65, "N": 0.78},
        tags=["婉约细腻", "才情孤高", "家国之痛"],
        quote="寻寻觅觅，冷冷清清，凄凄惨惨戚戚。",
        personality_keyword="细腻才情型",
    ),
    CharacterData(
        character_id="mock-yuefei",
        name="岳飞",
        source="历史",
        era="宋朝",
        description="南宋抗金名将，民族英雄。精忠报国，治军严明，勇冠三军，终因朝廷和议含冤而死。",
        ocean_vector={"O": 0.65, "C": 0.88, "E": 0.60, "A": 0.82, "N": 0.50},
        tags=["精忠报国", "治军严明", "壮志未酬"],
        quote="莫等闲，白了少年头，空悲切。",
        personality_keyword="忠勇刚烈型",
    ),
    CharacterData(
        character_id="mock-xinqiji",
        name="辛弃疾",
        source="历史",
        era="宋朝",
        description="南宋豪放派词人、爱国将领。文能填词武能杀敌，一生力主北伐，壮志难酬，悲歌慷慨。",
        ocean_vector={"O": 0.85, "C": 0.75, "E": 0.70, "A": 0.68, "N": 0.55},
        tags=["豪放悲歌", "壮志未酬", "文武兼备"],
        quote="了却君王天下事，赢得生前身后名。",
        personality_keyword="豪迈壮烈型",
    ),
    # ---------- 明清 ----------
    CharacterData(
        character_id="mock-wangyangming",
        name="王阳明",
        source="历史",
        era="明朝",
        description="心学集大成者，思想家、军事家。知行合一，致良知，文武双全，影响东亚数百年。",
        ocean_vector={"O": 0.90, "C": 0.85, "E": 0.65, "A": 0.72, "N": 0.30},
        tags=["知行合一", "致良知", "心学宗师"],
        quote="无善无恶心之体，有善有恶意之动。",
        personality_keyword="知行睿智型",
    ),
    CharacterData(
        character_id="mock-nalanxingde",
        name="纳兰性德",
        source="历史",
        era="清朝",
        description="清代词人，满洲贵胄。词风清丽婉约，多情善感，虽身处显贵却性情真挚孤寂，英年早逝。",
        ocean_vector={"O": 0.88, "C": 0.55, "E": 0.35, "A": 0.75, "N": 0.80},
        tags=["清丽多情", "孤寂真挚", "贵胄词心"],
        quote="人生若只如初见，何事秋风悲画扇。",
        personality_keyword="多情清婉型",
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

    新策略（11轮固定遍历 + 之后按 OCEAN 不确定性喂饭），详见
    select_next_dimension 的文档字符串。

    支持跳过冷却机制：被标记为"不舒服/拒绝"的维度，在冷却期内（默认3轮）
    暂时排除，冷却结束后若仍未探索过，会自动回来。

    参数:
        state: 当前会话状态

    返回:
        选定的维度 ID
    """
    dimension_uncertainty = state.get_dimension_uncertainty()
    exploration_counts = state.get_exploration_counts()
    # OCEAN 五维不确定性 —— 阶段二喂饭的核心依据
    ocean_uncertainty = {
        "O": state.ocean_vector.openness_uncertainty,
        "C": state.ocean_vector.conscientiousness_uncertainty,
        "E": state.ocean_vector.extraversion_uncertainty,
        "A": state.ocean_vector.agreeableness_uncertainty,
        "N": state.ocean_vector.neuroticism_uncertainty,
    }

    next_dim = select_next_dimension(
        dimension_uncertainty=dimension_uncertainty,
        exploration_counts=exploration_counts,
        ocean_uncertainty=ocean_uncertainty,
        total_rounds=state.turn_count,
        skipped_dimensions=getattr(state, "skipped_dimensions", None),
        cooldown_rounds=3,
    )
    state.current_dimension = next_dim

    # 判断是否为冷却回来的维度（需要柔和化提示）
    skipped = getattr(state, "skipped_dimensions", {}) or {}
    gentle = next_dim in skipped
    dim = get_dimension_by_id(next_dim)
    logger.info(
        f"[{state.session_id}] 选定下一维度: {next_dim}({dim.name})"
        f"{' [柔和化重试]' if gentle else ''}"
    )
    return next_dim


# ============================================================
# 节点 3：生成问题
# ============================================================

def generate_question_node(state: AgentState) -> str:
    """
    生成问题节点

    基于当前维度、对话历史、人格状态生成下一个问题。
    LLM 调用失败时自动 fallback 到该维度的备用问题，并加入共情回应。

    参数:
        state: 当前会话状态

    返回:
        问题文本
    """
    dimension_id = state.current_dimension

    # Mock 模式：跳过 LLM 调用，直接用该维度的备用问题池
    # 开发阶段节省智谱额度，且响应快
    if getattr(state, "use_mock", False):
        dim = get_dimension_by_id(dimension_id)
        question = dim.get_random_question()
        logger.info(f"[{state.session_id}] [Mock] 问题取自备用池(维度:{dimension_id})")
        return question

    # 构建历史（generate_question 内部保留全部历史避免重复）
    # history 格式要求 [{"question": "...", "answer": "..."}]
    history_for_generation = _build_history_for_question(state.history)

    # 当前 OCEAN 分数
    current_ocean = state.get_ocean_dict()

    # 该维度是否曾被跳过（需柔和化重试）
    gentle_retry = dimension_id in (getattr(state, "skipped_dimensions", {}) or {})

    try:
        result = _generate_question(
            dimension_id=dimension_id,
            history=history_for_generation,
            current_ocean=current_ocean,
            gentle_retry=gentle_retry,
        )
        question = result["question"]
        source = result.get("source", "ai")

        # 是否是「首问题」：还没有任何用户的回答，不应该出现共情回应（否则就变成瞎编用户情绪了）
        has_any_user_answer = any(h.get("role") == "user" and h.get("content") for h in state.history)

        # Fallback 问题（LLM 失败或解析失败）→ 只有存在用户回答时才加共情前缀
        if source == "fallback":
            if has_any_user_answer:
                recent_emp = _get_recent_empathies(state.history)
                empathy_prefix = _build_fallback_empathy(state.history, exclude=recent_emp)
                if empathy_prefix:
                    question = f"{empathy_prefix}{question}"
                logger.warning(f"[{state.session_id}] 使用fallback问题(维度:{dimension_id})，已加共情前缀")
            else:
                logger.warning(f"[{state.session_id}] 使用fallback问题(维度:{dimension_id})，首轮无用户回答，跳过共情前缀")
        else:
            # AI 生成的问题：仅当存在用户回答时才检测/补共情前缀
            # 首问题（没有任何历史回答）让 LLM 直接输出纯问题，不写共情
            if has_any_user_answer:
                question = _ensure_empathy_prefix(question, state.history)
            else:
                # 首问题兜底：如果 LLM 还是写了共情开头（「能感受到/原来…」），把它剥离掉
                stripped = _strip_empathy_prefix(question)
                if stripped != question:
                    logger.info(f"[{state.session_id}] 首问题检测到冗余共情前缀，已剥离")
                question = stripped

        logger.info(f"[{state.session_id}] 问题生成成功(维度:{dimension_id}{'，柔和化重试' if gentle_retry else ''}, source={source})")
    except Exception as e:
        # _generate_question 内部已 try-except，不会抛到这里
        # 但做防御性处理
        logger.error(f"[{state.session_id}] 问题生成异常({e})，使用备用问题+共情")
        dim = get_dimension_by_id(dimension_id)
        fallback = dim.get_random_question()
        # 异常兜底：首问题（没有任何历史回答）不加共情前缀
        has_any_user_answer = any(h.get("role") == "user" and h.get("content") for h in state.history)
        if has_any_user_answer:
            recent_emp = _get_recent_empathies(state.history)
            empathy_prefix = _build_fallback_empathy(state.history, exclude=recent_emp)
            question = f"{empathy_prefix}{fallback}" if empathy_prefix else fallback
        else:
            question = fallback

    return question


def _get_recent_empathies(history: List[Dict], max_rounds: int = 5) -> List[str]:
    """
    从对话历史中提取最近N轮已使用的共情前缀，用于避免重复

    参数:
        history: 对话历史
        max_rounds: 检查最近几轮

    返回:
        最近使用的共情前缀列表（按时间倒序）
    """
    recent_empathies = []
    ai_messages = [h for h in history if h.get("role") == "assistant"]
    for msg in reversed(ai_messages[-max_rounds:]):
        content = msg.get("content", "")
        if not content:
            continue
        # 提取前40字中的共情前缀
        for sep in ["。", "！", "，", ","]:
            idx = content.find(sep)
            if 0 < idx < 40:
                first_clause = content[:idx+1]
                if len(first_clause) >= 4:
                    recent_empathies.append(first_clause)
                    break
    return recent_empathies


def _ensure_empathy_prefix(question: str, history: List[Dict]) -> str:
    """
    检测 AI 生成的问题是否已包含共情回应，没有则自动补上。

    同时检查共情前缀是否与最近5轮重复，若重复则更换。

    参数:
        question: AI 生成的问题文本
        history: 对话历史

    返回:
        确保有共情前缀的问题文本
    """
    if not history:
        return question

    # 找最后一条用户消息
    last_user_answer = ""
    for h in reversed(history):
        if h.get("role") == "user":
            last_user_answer = h.get("content", "")
            break

    if not last_user_answer:
        return question

    # 扩展的共情识别词表
    empathy_indicators = [
        "能感受", "能理解", "原来", "明白了", "确实", "看得出来",
        "听得出来", "是这样", "了解", "说明你", "这表明",
        "听起来", "这说明", "能看出", "懂", "这确实",
        "看得出", "听得", "发现你", "感觉你",
        "想不到", "没想到", "能体会", "能感觉到",
        "看出来你", "感觉得到", "值得注意",
        "有意思", "有趣", "特别", "原来如此",
        "你习惯", "你在那", "愿意", "想不到",
    ]
    prefix = question[:40]
    has_empathy = any(w in prefix for w in empathy_indicators)

    # 获取最近5轮已用共情前缀
    recent = _get_recent_empathies(history)

    if has_empathy:
        # 检查当前共情前缀是否与最近重复
        already_used = False
        for old_emp in recent:
            if old_emp and old_emp in question[:40]:
                already_used = True
                break
        
        if not already_used:
            return question  # 有共情且不重复

        # 重复了，剥离原前缀，用新的替换
        for sep in ["。", "！", "，", ","]:
            idx = question.find(sep)
            if 0 < idx < 40:
                question = question[idx+1:].lstrip("，, ")
                break

    # 生成不重复的共情前缀
    empathy = _build_fallback_empathy(history, exclude=recent)
    if empathy:
        return f"{empathy}{question}"
    return question


def _build_fallback_empathy(history: List[Dict], exclude: List[str] = None) -> str:
    """
    从对话历史中提取最后一条用户回答，生成共情前缀

    根据回答内容的关键词匹配不同类别，每类有多个模板随机选择，
    避免每次都用同一种说法。支持排除已使用的模板。

    参数:
        history: AgentState 中的对话历史
        exclude: 需要排除的已用共情前缀列表

    返回:
        共情前缀文本，如 "看得出你是个很重过程的人。" 或空字符串
    """
    import random

    if exclude is None:
        exclude = []

    # 找最后一条用户消息
    last_user_answer = ""
    for h in reversed(history):
        if h.get("role") == "user":
            last_user_answer = h.get("content", "")
            break

    if not last_user_answer:
        return ""

    # 按回答内容的情感/行为特征分类，每类多个模板随机选
    # 模板设计原则：口语化、不重复、像真人朋友在聊天、不用"嗯"
    if any(kw in last_user_answer for kw in ["不想", "不愿", "不喜欢", "讨厌", "拒绝", "排斥", "逃避"]):
        # 回避/拒绝类
        templates = [
            "看得出来你对这个有点抵触。",
            "这确实不是你爱碰的事。",
            "能理解，有些事确实让人想绕开。",
            "这种事确实挺让人头疼的。",
            "懂，能感觉到你不太想碰这块。",
        ]
    elif any(kw in last_user_answer for kw in ["喜欢", "享受", "偏爱", "热爱", "感兴趣", "好奇"]):
        # 喜好/热爱类
        templates = [
            "看得出你在这方面挺有热情的。",
            "能感觉说到这个你眼睛都亮了。",
            "这确实是你喜欢的方向。",
            "听得出来你挺享受这种状态的。",
            "看得出来，这是你会投入精力的事。",
        ]
    elif any(kw in last_user_answer for kw in ["纠结", "犹豫", "矛盾", "两难", "不知道怎么", "拿不定"]):
        # 纠结/犹豫类
        templates = [
            "能感觉到你当时确实有点拿不准。",
            "这种事确实让人左右为难。",
            "能想象你当时在脑子里反复权衡的样子。",
            "听得出来，这个选择对你来说不太轻松。",
            "确实是那种怎么选都觉得差点意思的情况。",
        ]
    elif any(kw in last_user_answer for kw in ["紧张", "焦虑", "担心", "害怕", "慌", "忐忑", "不安"]):
        # 焦虑/紧张类
        templates = [
            "能感觉到那件事让你挺有压力的。",
            "那种忐忑的感觉确实不好受。",
            "看得出来你在那件事上背负了不少。",
            "能理解，那种不确定感确实挺磨人的。",
            "听得出来你当时心里不太踏实。",
        ]
    elif any(kw in last_user_answer for kw in ["努力", "坚持", "硬着", "咬牙", "扛", "拼", "奋斗"]):
        # 努力/坚持类
        templates = [
            "看得出来你是个能扛事的人。",
            "你在那件事上确实下了不少功夫。",
            "能感觉到你骨子里有股不服输的劲儿。",
            "听得出来，你是那种会逼自己一把的人。",
            "看得出来，就算难你也不会轻易放弃。",
        ]
    elif any(kw in last_user_answer for kw in ["一个人", "独自", "自己", "独处", "安静", "一个人待"]):
        # 独处/内向类
        templates = [
            "看得出你挺享受自己一个人待着的时光。",
            "独处对你来说更像是充电。",
            "能理解，人在安静的时候反而想得更清楚。",
            "看得出来你是那种能从独处中获得能量的人。",
            "懂，有些事确实更适合一个人慢慢消化。",
        ]
    elif any(kw in last_user_answer for kw in ["朋友", "一起", "团队", "合作", "商量", "找人"]):
        # 社交/合作类
        templates = [
            "看得出来你挺重视身边人的。",
            "能感觉到你在关系里是会考虑对方的。",
            "能理解，有些事确实需要有人一起分担。",
            "听得出来你蛮在意和别人的互动方式的。",
            "看得出，你在人际交往上有自己的节奏。",
        ]
    elif any(kw in last_user_answer for kw in ["计划", "目标", "规划", "安排", "清单", "条理"]):
        # 计划/条理类
        templates = [
            "看得出你是个做事有条理的人。",
            "你习惯把事情理清楚了再动手。",
            "能感觉到你对自己要做什么心里有数。",
            "听得出来你是那种先想好再走的人。",
            "看得出，比起随机应变你更擅长提前布局。",
        ]
    elif any(kw in last_user_answer for kw in ["乐观", "相信", "希望", "总会好的", "往好处想"]):
        # 乐观/积极类
        templates = [
            "看得出来你是个骨子里偏乐观的人。",
            "能感觉到你习惯往好的方向看。",
            "能理解，有些时候心态确实比结果重要。",
            "听得出你是那种相信事情会有转机的人。",
            "看得出，你不会轻易被困难打垮。",
        ]
    elif any(kw in last_user_answer for kw in ["细节", "认真", "仔细", "精益求精", "完美", "讲究"]):
        # 细节/认真类
        templates = [
            "看得出你做事蛮讲究的。",
            "能感觉到你对细节有自己的标准。",
            "听得出来你不是那种差不多就行的人。",
            "看得出来，你会把事情做到自己满意为止。",
            "能理解，有些东西确实值得多花点心思。",
        ]
    elif any(kw in last_user_answer for kw in ["怀疑", "不够好", "自我怀疑", "反思", "改进", "不足"]):
        # 自我反思类
        templates = [
            "能感觉到你对自己有挺高的要求。",
            "愿意这样审视自己的人不多。",
            "看得出来你在一直想办法变得更好。",
            "听得出来你是那种会反复琢磨自己的人。",
            "能理解，有些时候确实不太容易对自己满意。",
        ]
    else:
        # 通用兜底
        templates = [
            "原来是这样。",
            "了解了。",
            "听得出来你有自己的想法。",
            "看得出来你是个有自己节奏的人。",
            "懂了，你的想法挺清楚的。",
            "能感觉到你思考过这件事。",
            "了解，每个人确实都有自己的方式。",
        ]

    # 过滤掉已使用的模板
    available = [t for t in templates if t not in exclude]
    if not available:
        available = templates  # 如果全被排除了，就用所有模板（避免空）

    return random.choice(available)


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

    Mock 模式（state.use_mock=True）：
       跳过 LLM 调用，生成合成 deltas 推进人格演化。
       合成策略：以当前 OCEAN 向量为基准，向随机方向施加大幅 delta
       （±0.08~0.12，远大于真实模式的上限），并在全部 5 维都给非零值。
       这样 15 轮内不确定性会均匀降到 0.1 以下，能触发真实收敛。
       目标是让 Mock 模式跑通完整闭环，便于前端开发验证。

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

    # ============================================================
    # Mock 模式：生成合成 OCEAN deltas，不调 LLM
    # ============================================================
    if getattr(state, "use_mock", False):
        ocean_delta = _generate_mock_ocean_delta(current_ocean, state)

        # 更新 11 维向量（记录分数变化和探索次数，与真实模式保持一致的更新路径）
        from src.personality.model import DIMENSION11_TO_OCEAN_MAPPING
        mapped_dims = DIMENSION11_TO_OCEAN_MAPPING.get(dimension, [])
        if mapped_dims:
            dim11_delta = sum(ocean_delta.get(d, 0.0) for d in mapped_dims) / len(mapped_dims)
        else:
            dim11_delta = 0.0
        updater.update_dimension11(state.dim11_vector, dimension, dim11_delta)

        # 用合成 deltas 更新 OCEAN（覆盖全部 5 维，确保不确定性均匀下降）
        updater.update_ocean(state.ocean_vector, ocean_delta)

        # 有效回答，轮次 + 1
        state.turn_count += 1

        logger.info(
            f"[{state.session_id}] [Mock] 人格更新成功(维度:{dimension}, 轮次:{state.turn_count}), "
            f"delta={ocean_delta}"
        )

        return {
            "success": True,
            "skipped": False,
            "guidance": None,
            "ocean_delta": ocean_delta,
        }

    # ============================================================
    # 真实模式：调 LLM 分析
    # ============================================================
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

    # 更新 11 维向量（仅记录该维度的分数变化和探索次数，用于维度选择策略）
    # 取该维度映射的 OCEAN 维度 deltas 的平均值作为 dim11 分数的变化量
    from src.personality.model import DIMENSION11_TO_OCEAN_MAPPING
    mapped_dims = DIMENSION11_TO_OCEAN_MAPPING.get(dimension, [])
    if mapped_dims:
        dim11_delta = sum(ocean_delta.get(d, 0.0) for d in mapped_dims) / len(mapped_dims)
    else:
        dim11_delta = 0.0
    updater.update_dimension11(state.dim11_vector, dimension, dim11_delta)

    # 用 LLM 给出的 OCEAN deltas 更新 OCEAN 向量（只更新一次）
    # update_ocean 内部会应用 smooth_update（边缘减速）并降低 OCEAN 不确定性
    updater.update_ocean(state.ocean_vector, ocean_delta)

    # 有效回答，轮次 + 1
    state.turn_count += 1

    # 该维度成功探索后，清除"被跳过"标记（不再需要柔和化）
    if dimension in (getattr(state, "skipped_dimensions", {}) or {}):
        state.skipped_dimensions.pop(dimension, None)
        logger.info(f"[{state.session_id}] 维度 {dimension} 柔和化重试成功，清除跳过标记")

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


def _generate_mock_ocean_delta(
    current_ocean: Dict[str, float],
    state: "AgentState",
) -> Dict[str, float]:
    """
    生成 Mock 模式下的合成 OCEAN deltas（不调 LLM）

    策略：
    - 每个维度在首次更新时随机选定一个稳定的方向签名（+1 / -1），
      存到 state.mock_ocean_signs 里并随 state_json 一起持久化，
      保证跨 HTTP 请求稳定演化、画像不漂移。
    - 已接近边缘（距 0/1 < 0.15）时把签名清零，停止推动，避免饱和到 0/1。
    - 加入 ±0.015 的小噪声，让演化曲线有真实感。

    设计目标：15~20 轮内 OCEAN 向量演化到一个稳定的"用户画像"
    （分数分散在 0.15~0.85 区间），不确定性均匀降到 0.1 以下，
    触发真实收敛并匹配到一个有区分度的人物。

    参数:
        current_ocean: 当前 OCEAN 分数，如 {"O": 0.55, ...}
        state: AgentState 实例（用于存取 mock_ocean_signs）

    返回:
        合成的 OCEAN deltas，如 {"O": 0.06, "C": -0.03, ...}
    """
    import random

    signs = state.mock_ocean_signs  # 由 AgentState 持有，跨请求持久化

    delta = {}
    for dim in ["O", "C", "E", "A", "N"]:
        current = current_ocean.get(dim, 0.5)

        # 首次：随机选定一个方向签名
        if dim not in signs or signs[dim] == 0 and 0.15 < current < 0.85:
            # 重新激活（如果之前停推但现在又回到中段，重新给个方向）
            if dim not in signs:
                signs[dim] = random.choice([1, -1])
        sign = signs.get(dim, 1)

        # 已接近边缘，停止推动，避免饱和到 0/1
        if (sign > 0 and current >= 0.85) or (sign < 0 and current <= 0.15):
            signs[dim] = 0
            delta[dim] = round(random.uniform(-0.01, 0.01), 3)  # 微抖
            continue

        # 推动幅度：剩余距离越大推得越多，越接近边缘推得越少（自然减速）
        if sign > 0:
            remaining = 0.85 - current
        else:
            remaining = current - 0.15

        magnitude = min(random.uniform(0.03, 0.06), remaining * 0.6 + 0.01)
        noise = random.uniform(-0.015, 0.015)
        delta[dim] = round(sign * magnitude + noise, 3)

    return delta


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
    收敛条件（满足任一即可）：
    A. 主路径：轮次 ≥ 15 且 OCEAN 平均不确定性 < 0.3
    B. 提前出口：轮次 ≥ 18 且 5 维中 ≥ 4 维不确定性 < 0.3
    C. 兜底出口：轮次 ≥ 20（强制收敛）

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

    # 记录收敛路径（normal / early / force），供日志和前端展示
    path = details.get("convergence_path", "none")
    if converged:
        logger.info(
            f"[{state.session_id}] 收敛命中: path={path}, "
            f"rounds={details['details']['total_rounds']}, "
            f"avg_unc={details['details']['ocean_uncertainty']:.3f}, "
            f"dim_below_thresh={details['details'].get('dimensions_below_threshold', 'N/A')}"
        )
    else:
        logger.info(
            f"[{state.session_id}] 未收敛: rounds={details['details']['total_rounds']}, "
            f"avg_unc={details['details']['ocean_uncertainty']:.3f}"
        )
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
