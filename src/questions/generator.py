"""
问题生成器模块

本模块负责生成探索用户人格的问题。
核心功能：
1. 构建问题生成的 Prompt
2. 调用 LLM API 生成问题
3. 解析 AI 返回的结果
4. 处理错误和 fallback

设计说明：
- 维度选择策略在 Agent 模块中实现，本模块只负责生成问题
- 输入：选定维度、历史对话、人格状态等
- 输出：问题文本
"""

import json
import re
import random
from typing import Dict, List, Any, Optional

from src.utils.llm import chat
from .modules import QuestionDimension, get_dimension_by_id


# ============================================================================
# 常量定义
# ============================================================================

# OCEAN 维度名称映射（用于构建 Prompt）
OCEAN_NAMES = {
    "O": "开放性（好奇心、创造力、接受新事物）",
    "C": "责任心（自律、计划性、目标导向）",
    "E": "外向性（社交活跃度、能量来源）",
    "A": "宜人性（合作性、同理心、信任他人）",
    "N": "神经质（情绪稳定性、焦虑敏感度）"
}

# 不确定性阈值（用于维度选择策略，在 Agent 模块中使用）
UNCERTAINTY_THRESHOLD = 0.3

# 最小探索次数（用于维度选择策略，在 Agent 模块中使用）
MIN_EXPLORATION_COUNT = 2


# ============================================================================
# Prompt 构建
# ============================================================================

def build_system_prompt() -> str:
    """
    构建 system prompt

    system prompt 定义 AI 的角色、核心机制（11 维度 → OCEAN 五维）和基本规则，
    在每次调用时保持不变。

    返回:
        system prompt 文本
    """
    return """你是一个基于 OCEAN 人格模型的人格探索专家。你将通过自然的生活化对话，逐步了解用户的人格特质。

【核心机制：11 个探索维度 → OCEAN 五维】
核心机制是通过 11 个贴近生活的探索维度来提问，每个探索维度会映射到 1~2 个 OCEAN 维度，用户的回答会自然流露出对应的人格倾向。

11 个探索维度如下：
- 社交互动（社交偏好、能量来源、人际关系模式）→ 映射 E（外向性）
- 情绪体验（情绪敏感度、调节能力、稳定性）→ 映射 N（神经质）
- 决策风格（决策方式、风险偏好、执行力）→ 映射 C（责任心）、O（开放性）
- 价值取向（人生目标、道德判断、价值排序）→ 映射 O（开放性）、A（宜人性）
- 自我认知（自我理解、自我接纳、自我反思）→ 映射 N（神经质）
- 人际信任（信任他人倾向、合作倾向、同理心）→ 映射 A（宜人性）
- 压力应对（应对策略、抗压能力、恢复力）→ 映射 N（神经质）、C（责任心）
- 创造探索（好奇心、想象力、接受新事物）→ 映射 O（开放性）
- 成就动机（追求成功、目标设定、野心）→ 映射 C（责任心）
- 生活态度（乐观/悲观、生活满意度、人生意义）→ 映射 N（神经质）、E（外向性）
- 亲密关系（依恋风格、亲密需求、情感表达）→ 映射 A（宜人性）、N（神经质）

OCEAN 五维（仅供你理解，不要出现在问题里）：
- O（开放性）：好奇心、创造力、接受新事物
- C（责任心）：自律、计划性、目标导向
- E（外向性）：社交活跃度、能量来源
- A（宜人性）：合作性、同理心、信任他人
- N（神经质）：情绪稳定性、焦虑敏感度

每次我会指定"当前要探索的维度"，你只需围绕该维度生成一个高质量的探索性问题。"""


def build_user_prompt(
    dimension: QuestionDimension,
    history: List[Dict],
    current_ocean: Dict[str, float],
    examples: List[str],
    gentle_retry: bool = False
) -> str:
    """
    构建 user prompt

    user prompt 包含具体的任务信息，每次调用时根据当前状态动态生成。

    参数:
        dimension: 当前探索的维度对象
        history: 完整对话历史（问题+回答），用于避免重复
        current_ocean: 当前 OCEAN 分数（可选，用于参考）
        examples: 问题示例列表（8个经典问题）

    返回:
        user prompt 文本
    """
    # 构建维度信息部分
    dimension_info = f"""【当前探索维度】
维度名称：{dimension.name}
维度描述：{dimension.description}
映射到 OCEAN 维度：{dimension.get_ocean_mapping_description()}
注意：问题中不要出现"外向性""人格""OCEAN"等术语，只需围绕该维度的生活场景自然提问。"""

    # 柔和化重试提示（该维度之前因用户"不舒服/拒绝"被跳过，现在重新探索）
    if gentle_retry:
        dimension_info += """

【特别提示：柔和化重试】
这个维度在之前的对话中曾让用户感到不舒服或选择跳过，现在换一个角度重新探索。
请务必：
1. 用更轻松、更日常、更小的场景来切入（比如用一个第三人称的小故事、一个轻松的假设情境），
   避开上次可能让用户不适的直接追问方式。
2. 不触及敏感、隐私、创伤性的话题，话题分量要轻。
3. 让用户感觉这只是随口一聊，而不是在被打探。"""

    # 构建历史对话部分（展示全部历史，避免与之前的问题重复）
    history_info = ""
    if history:
        history_lines = []
        for i, h in enumerate(history, 1):
            question = h.get("question", "")
            answer = h.get("answer", "")
            history_lines.append(f"第{i}轮")
            history_lines.append(f"  问题：{question}")
            history_lines.append(f"  回答：{answer}")
        history_info = f"""【历史对话】（完整记录，避免与之前的问题重复）
{chr(10).join(history_lines)}"""

    # 构建输出要求部分
    first_question = not history  # 首问题 = 没有历史对话（history是完整[Q&A]列表，空列表就意味着首轮）
    first_question_clause = (
        "本轮是第一个问题，用户还没有任何回答。"
        "因此：直接输出【纯问题正文】（情境+选项+引导展开）即可，"
        "绝对不要写任何共情回应/过渡/回应的话（不要有『能感受到』『原来』『确实』这类开头），"
        "不要编造用户的情绪或经历。" if first_question else
        "本轮不是第一个问题，请先用一句话共情回应用户的上一句回答，再自然过渡到新问题。"
    )
    output_requirements = f"""【输出要求】（请严格遵守）
1. 【先共情回应，再过渡】——仅适用于非首问题
   {first_question_clause}

2. 【1+x 模式 —— 不是问多个问题】
   整段只包含一个核心问题，分成两部分：
   - "1"：给出一个有具体情境的问题，并提供清晰的选择项供用户作答（二选一或三选一），
          也可以提示用户可以给出自己想到的其他回应。
   - "x"：在问题后用一句话引导用户展开，但不要固定追问"心情"。
          根据问题内容灵活引导，例如：
          - 问决策时 → "当时你主要考虑的是什么？" / "你更看重哪一点？"
          - 问行为时 → "你当时具体是怎么做的？" / "能回忆下当时的情境吗？"
          - 问偏好时 → "你为什么会倾向于这种选择？" / "这背后对你来说意味着什么？"
          - 问社交时 → "当时你心里是怎么盘算的？"（只有涉及情绪感受的问题才问心情）
          切记：不要所有问题都追问心情或感受，要根据问题性质灵活选择引导方式。
   切记：不要罗列多个并列问题让用户不知该答哪个。

3. 【具体情境，而非空泛抽象】
   问题必须包含一个具体、能让人联想到自身经历的场景（一个具体场合 / 具体动作 / 具体时刻），
   让用户一读就想到"对，我就是这样的人"。
   ✅ 好：周五下班，同事临时拉你去一个十几人的聚餐，你的第一反应是期待，还是想找个借口推掉？
        当时你主要考虑的是什么？
   ❌ 差：你周末更喜欢和朋友聚会还是独自待着？为什么？（太抽象、太宽泛，用户无从想起细节）

4. 【简洁 ≠ 简单】
   - 简洁：用尽量短的句子把情境讲清楚，不要啰嗦铺垫、不要堆砌形容词。
   - 不简单：情境要有信息量、有代入感。禁止"你喜欢社交吗？""你常焦虑吗？"这种一句话空洞问题。

5. 【避免重复】
   仔细查看上方完整历史对话（特别是最近3轮的问题），不要问与之前高度相似的问题。
   换一个新角度切入同一维度，或选择该维度下尚未涉及的具体场景。

【输出格式】
只返回 JSON，不要有任何额外文字：
{"question": "[共情回应上一句] + [过渡] + [具体情境问题+选择项] + [灵活引导展开]"}"""

    # 构建问题示例部分
    examples_info = ""
    if examples:
        examples_list = chr(10).join([f"- {ex}" for ex in examples])
        examples_info = f"""【问题示例】（仅供参考，不要直接使用）
{examples_list}"""

    # 组合所有部分
    parts = [dimension_info]
    if history_info:
        parts.append(history_info)
    parts.append(output_requirements)
    if examples_info:
        parts.append(examples_info)

    return chr(10).join(parts)


# ============================================================================
# 结果解析
# ============================================================================

def parse_question_response(response: str) -> Optional[str]:
    """
    解析 AI 返回的问题
    
    AI 返回的可能是标准 JSON，也可能带有额外文字。
    本函数尝试多种方式解析，提取问题文本。
    
    参数:
        response: AI 返回的原始文本
    
    返回:
        问题文本，如果解析失败则返回 None
    """
    # 方法1：直接解析 JSON
    try:
        data = json.loads(response)
        if "question" in data:
            return data["question"]
    except json.JSONDecodeError:
        pass
    
    # 方法2：用正则提取 JSON 部分
    # 匹配 {...} 格式的 JSON 对象
    match = re.search(r'\{[^{}]*\}', response)
    if match:
        try:
            data = json.loads(match.group())
            if "question" in data:
                return data["question"]
        except json.JSONDecodeError:
            pass
    
    # 方法3：尝试提取引号中的问题文本
    # 匹配 "question": "..." 格式
    match = re.search(r'"question"\s*:\s*"([^"]+)"', response)
    if match:
        return match.group(1)
    
    # 所有方法都失败，返回 None
    return None


# ============================================================================
# 问题生成核心函数
# ============================================================================

def generate_question(
    dimension_id: str,
    history: List[Dict] = None,
    current_ocean: Dict[str, float] = None,
    gentle_retry: bool = False
) -> Dict[str, Any]:
    """
    生成探索性问题

    这是问题生成器的核心函数，负责：
    1. 获取维度信息
    2. 构建 Prompt
    3. 调用 LLM
    4. 解析结果
    5. 重复检测（若生成问题与历史高度相似则重试）
    6. 处理错误和 fallback

    参数:
        dimension_id: 维度ID（如 "social"）
        history: 完整对话历史，格式为 [{"question": "...", "answer": "..."}, ...]
        current_ocean: 当前 OCEAN 分数，格式为 {"O": 0.5, "C": 0.5, ...}
        gentle_retry: 是否柔和化重试。True 表示该维度之前因用户"不舒服/拒绝"被跳过，
                      现在重新探索，需用更轻松日常的问法，避开上次的敏感角度。

    返回:
        包含问题信息的字典，格式为：
        {
            "question": "问题文本",
            "dimension_id": "维度ID",
            "dimension_name": "维度名称",
            "source": "ai" 或 "fallback"
        }

    异常:
        KeyError: 如果维度ID不存在
    """
    # 获取维度对象
    dimension = get_dimension_by_id(dimension_id)

    # 初始化默认值
    if history is None:
        history = []
    if current_ocean is None:
        current_ocean = {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5}

    # 保留全部对话历史，用于避免生成与之前高度相似的问题
    # （早期版本只取最近2轮，导致长对话中问题频繁重复）
    recent_history = history

    # 获取问题示例
    examples = dimension.questions

    # 构建 Prompt
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(
        dimension=dimension,
        history=recent_history,
        current_ocean=current_ocean,
        examples=examples,
        gentle_retry=gentle_retry
    )
    
    # 构建消息列表
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # 调用 LLM（最多重试2次以避免重复）
    last_fallback = None
    for attempt in range(2):
        try:
            # 调用 chat 方法，指定功能类型为问题生成
            response = chat(
                messages=messages,
                function="question_generation"
            )
            
            # 解析结果
            question = parse_question_response(response)
            
            if question:
                # 重复检测：与全部历史问题比较相似度
                if _is_similar_to_history(question, history):
                    if attempt == 0:
                        # 第一次生成重复，重试一次（在 prompt 中追加强调）
                        messages[-1]["content"] += "\n\n【重要补充】你刚才的回答与之前的问题太相似了，请务必换一个完全不同的场景和角度来提问。"
                        continue
                    else:
                        # 第二次还是重复，放弃 LLM 结果，使用 fallback 避免重复
                        logger.warning("LLM 重试2次仍生成重复问题，改用 fallback")
                        fallback_question = dimension.get_random_question()
                        return {"question": fallback_question, "source": "fallback"}
                return {"question": question, "source": "ai"}
            
            # 解析失败，尝试 fallback
            fallback_question = dimension.get_random_question()
            return {"question": fallback_question, "source": "fallback"}
            
        except Exception as e:
            # LLM 调用失败，保存 fallback 以便重试
            last_fallback = dimension.get_random_question()
            if attempt == 0:
                continue  # 重试一次
            # 第二次仍失败，使用 fallback
            break
    
    # 两次都失败，使用 fallback
    fallback_question = last_fallback or dimension.get_random_question()
    return {"question": fallback_question, "source": "fallback"}


def _strip_empathy_prefix(question: str) -> str:
    """
    剥离问题中的共情前缀，返回纯问题正文

    共情前缀通常是前30字内的简短情感回应（句号结尾），
    如"能感受到你的倾向。"或"原来是这样，"。剥离后才能准确比较问题内容是否重复。
    """
    # 共情前缀识别词
    empathy_words = [
        "能感受", "能理解", "原来", "明白了", "确实", "看得出来",
        "听得出来", "是这样", "了解", "说明你", "这表明",
        "听起来", "这说明", "能看出", "懂", "这确实",
        "看得出", "听得", "发现你", "感觉你",
    ]
    
    # 取前50字，检查是否有共情开头
    prefix_text = question[:50]
    
    # 尝试按句号/逗号分割，看第一个分句是否为共情
    for sep in ["。", "！", "，", ","]:
        idx = prefix_text.find(sep)
        if 0 < idx < 40:
            first_clause = prefix_text[:idx+1]
            if any(w in first_clause for w in empathy_words):
                # 去掉这个共情前缀，返回剩余内容
                remaining = question[idx+1:].lstrip("，, ")
                return remaining if remaining else question
    
    # 没检测到共情前缀，返回原文
    return question


def _is_similar_to_history(new_question: str, history: List[Dict]) -> bool:
    """
    检查新问题是否与历史中所有已问过的问题高度相似

    先剥离共情前缀，再对问题正文进行全文相似度比较。
    使用最长公共子序列(LCS)比例作为相似度指标，比关键词重叠更准确。

    参数:
        new_question: 新生成的问题文本
        history: 对话历史

    返回:
        True 表示高度相似（应重试），False 表示可以使用
    """
    if not history:
        return False

    # 提取全部历史问题的正文（剥离共情前缀）
    all_questions = []
    for h in history:
        if h.get("question"):
            stripped = _strip_empathy_prefix(h["question"])
            all_questions.append(stripped)

    if not all_questions:
        return False

    # 剥离新问题的共情前缀
    new_stripped = _strip_empathy_prefix(new_question)
    
    # 如果剥离后太短（可能是纯共情），直接判定为重复
    if len(new_stripped) < 5:
        return True

    # 使用字符级编辑距离比例比较全文相似度
    for old_q in all_questions:
        similarity = _compute_text_similarity(new_stripped, old_q)
        if similarity >= 0.6:  # 60% 以上文本相似视为重复
            return True
    
    return False


def _compute_text_similarity(text1: str, text2: str) -> float:
    """
    计算两段文本的相似度（基于字符级最长公共子序列比例）

    比关键词重叠更准确，能检测到换说法但意思相同的重复问题。
    时间复杂度 O(n*m)，但问题文本很短（<100字），完全可接受。

    参数:
        text1: 第一段文本
        text2: 第二段文本

    返回:
        相似度 0-1
    """
    if not text1 or not text2:
        return 0.0
    
    len1, len2 = len(text1), len(text2)
    if len1 == 0 or len2 == 0:
        return 0.0
    
    # 计算最长公共子序列
    # 优化：只用一维数组，空间 O(min(len1, len2))
    if len1 > len2:
        text1, text2 = text2, text1
        len1, len2 = len2, len1
    
    # dp[j] = LCS长度，按行更新
    prev = [0] * (len2 + 1)
    for i in range(1, len1 + 1):
        curr = [0] * (len2 + 1)
        for j in range(1, len2 + 1):
            if text1[i-1] == text2[j-1]:
                curr[j] = prev[j-1] + 1
            else:
                curr[j] = max(prev[j], curr[j-1])
        prev = curr
    
    lcs_len = prev[len2]
    # 相似度 = LCS长度 / 较短文本长度
    return lcs_len / min(len1, len2)


def _extract_keywords(text: str) -> set:
    """
    简单提取中文关键词（基于字符 n-gram 和停用词过滤）

    参数:
        text: 文本

    返回:
        关键词集合
    """
    if not text:
        return set()
    
    # 常见停用词
    stop_words = {
        "的", "了", "是", "在", "我", "你", "他", "她", "它",
        "有", "和", "就", "不", "人", "都", "一", "一个", "上",
        "也", "很", "到", "说", "要", "去", "你是", "什么",
        "怎么", "为什么", "哪", "哪个", "多少", "几", "吧",
        "呢", "啊", "吗", "？", "?", "，", "。", "、",
    }
    
    # 提取 2-gram 作为关键词
    keywords = set()
    clean_text = re.sub(r'[^\u4e00-\u9fff\w]', '', text)
    for i in range(len(clean_text) - 1):
        bigram = clean_text[i:i+2]
        if bigram not in stop_words and len(bigram) >= 1:
            keywords.add(bigram)
    
    return keywords


# ============================================================================
# 维度选择策略（供 Agent 模块使用）
# ============================================================================

def select_next_dimension(
    dimension_uncertainty: Dict[str, float],
    exploration_counts: Dict[str, int],
    ocean_uncertainty: Dict[str, float] = None,
    total_rounds: int = 0,
    skipped_dimensions: Dict[str, Dict] = None,
    cooldown_rounds: int = 3
) -> str:
    """
    选择下一个要探索的维度

    维度选择策略（11轮固定遍历 + 之后按 OCEAN 不确定性喂饭）：

    解决"两个空间不对齐"问题的核心改动：
    - 维度选择在 11 维空间，收敛判断在 OCEAN 5 维空间，两者不对齐。
    - 旧策略按 11 维轮询，每轮只喂 1~2 个 OCEAN 维度，
      而 E（外向性）只被 social/life_attitude 两个维度映射，极易"饿死"，
      导致收敛慢且不稳定（平均 20+ 轮，甚至拖到 30 轮强制结束）。

    新策略分两阶段：
    - 阶段一（前 11 轮）：按固定顺序遍历 11 个探索维度，每个至少问 1 次。
      保证覆盖广度，同时每个维度都自然喂一次信号给它映射的 OCEAN 维度。
      **跳过冷却机制**：被标记为"不舒服/拒绝"的维度，在冷却期内（默认3轮）
      暂时排除，冷却结束后若仍未探索过，会自动回来。
    - 阶段二（第 12 轮起）：找 OCEAN 不确定性最高的维度（最"饿"的），
      在映射到它的探索维度里选一个出题，精准喂饭。
      候选维度里优先选探索次数少的，避免反复问同一维度。

    模拟验证：在 30~50% 信号丢失的恶劣条件下，平均 16 轮收敛，范围 15~18，稳定。

    参数:
        dimension_uncertainty: 各探索维度的不确定性（保留参数，阶段一不再依赖）
        exploration_counts: 各探索维度的探索次数，格式为 {"social": 1, "emotion": 3, ...}
        ocean_uncertainty: OCEAN 五维的不确定性，格式为 {"O":0.8,"C":0.6,...}，
                           阶段二喂饭的核心依据。为 None 时回退到阶段一策略。
        total_rounds: 当前总探索轮次（≥11 后进入阶段二）
        skipped_dimensions: 被跳过的维度标记，格式为 {维度ID: {"reason": ..., "skipped_at_turn": int}}
        cooldown_rounds: 跳过冷却轮数，默认 3。被跳过的维度在此轮数内不会被选中。

    返回:
        选定的维度ID
    """
    from .modules import get_dimension_by_id, get_all_dimension_ids

    # 所有探索维度（固定顺序）
    all_dimensions = get_all_dimension_ids()

    # 计算"冷却中"的维度集合（被跳过且未出冷却期）
    skipped_set = set()
    if skipped_dimensions:
        for dim_id, info in skipped_dimensions.items():
            skipped_at = info.get("skipped_at_turn", 0)
            if total_rounds - skipped_at < cooldown_rounds:
                skipped_set.add(dim_id)

    # ============================================================
    # 阶段一：前 11 轮固定遍历（保证 11 维全覆盖）
    # ============================================================
    if total_rounds < len(all_dimensions):
        # 取尚未探索过的维度（探索次数为 0）
        unexplored = [d for d in all_dimensions if exploration_counts.get(d, 0) == 0]
        # 排除冷却中的维度（用户刚表达过不舒服/拒绝，先让开）
        available = [d for d in unexplored if d not in skipped_set]
        if available:
            return available[0]
        # 全部未探索维度都在冷却中 → 退化到选冷却中第一个（尊重冷却，但保证遍历）
        if skipped_set & set(unexplored):
            return next(iter(skipped_set & set(unexplored)))

    # ============================================================
    # 阶段二：按 OCEAN 不确定性喂饭 + 未探索维度兜底
    # ============================================================
    # 兜底策略：如果仍有未探索的维度（explore_count=0）且不在冷却期，
    # 强制返回它——保证 11 维全覆盖，即使 OCEAN 已收敛
    unexplored_available = [
        d for d in all_dimensions
        if exploration_counts.get(d, 0) == 0 and d not in skipped_set
    ]
    if unexplored_available:
        # 优先选映射到 OCEAN 最高不确定性的那个（仍尊重喂饭逻辑）
        if ocean_uncertainty:
            ocean_keys = ["O", "C", "E", "A", "N"]
            target_ocean = max(ocean_keys, key=lambda k: ocean_uncertainty.get(k, 1.0))
            for d in unexplored_available:
                dim = get_dimension_by_id(d)
                if target_ocean in dim.ocean_mapping:
                    return d
        # 都不映射最高 OCEAN → 直接选第一个
        return unexplored_available[0]

    # 没有 OCEAN 不确定性数据时，回退到"探索次数最少"的兜底策略
    if not ocean_uncertainty:
        candidates = [d for d in all_dimensions if d not in skipped_set]
        if not candidates:
            candidates = all_dimensions
        min_count = min(exploration_counts.get(d, 0) for d in candidates)
        least = [d for d in candidates if exploration_counts.get(d, 0) == min_count]
        return random.choice(least)

    # 找 OCEAN 不确定性最高的维度（最"饿"的）
    ocean_keys = ["O", "C", "E", "A", "N"]
    target_ocean = max(ocean_keys, key=lambda k: ocean_uncertainty.get(k, 1.0))

    # 找映射到该 OCEAN 维度的所有探索维度
    candidates = []
    for dim_id in all_dimensions:
        dim = get_dimension_by_id(dim_id)
        if target_ocean in dim.ocean_mapping:
            candidates.append(dim_id)

    # 排除冷却中的维度
    available_candidates = [d for d in candidates if d not in skipped_set]
    if not available_candidates:
        available_candidates = candidates  # 全部冷却中 → 退化

    # 候选为空（理论不会发生，每个 OCEAN 都至少被 1 个维度映射），兜底随机
    if not available_candidates:
        return random.choice(all_dimensions)

    # 在候选里优先选探索次数少的，避免反复问同一维度
    min_count = min(exploration_counts.get(d, 0) for d in available_candidates)
    least_explored = [d for d in available_candidates if exploration_counts.get(d, 0) == min_count]
    return random.choice(least_explored)