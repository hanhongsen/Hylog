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

    # Mock 模式：跳过 LLM 调用，直接用该维度的备用问题池
    # 开发阶段节省智谱额度，且响应快
    if getattr(state, "use_mock", False):
        dim = get_dimension_by_id(dimension_id)
        question = dim.get_random_question()
        logger.info(f"[{state.session_id}] [Mock] 问题取自备用池(维度:{dimension_id})")
        return question

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

        # 计算 11 维的变化量（取该维度映射的 OCEAN 维度 deltas 的平均值）
        from src.personality.model import DIMENSION11_TO_OCEAN_MAPPING
        mapped_dims = DIMENSION11_TO_OCEAN_MAPPING.get(dimension, [])
        if mapped_dims:
            dim11_delta = sum(ocean_delta.get(d, 0.0) for d in mapped_dims) / len(mapped_dims)
        else:
            dim11_delta = 0.0

        # 更新 11 维和 OCEAN（与真实模式保持一致的更新路径）
        updater.update_ocean_from_dimension11(
            ocean_vector=state.ocean_vector,
            dim11_vector=state.dim11_vector,
            dimension=dimension,
            delta=dim11_delta,
        )
        # 直接用合成 deltas 覆盖更新一次（覆盖全部 5 维，确保不确定性均匀下降）
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
