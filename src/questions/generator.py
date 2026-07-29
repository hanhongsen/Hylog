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
    examples: List[str]
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
    output_requirements = """【输出要求】（请严格遵守）
1. 【先共情回应，再过渡】
   除本轮第一个问题外，每次都要先用一句话、用共情的方式回应用户的上一句回答
   （比如"能感受到你那时确实有点纠结"），一句话即可，不要长篇大论，
   然后自然过渡到新问题。

2. 【1+x 模式 —— 不是问多个问题】
   整段只包含一个核心问题，分成两部分：
   - "1"：给出一个有具体情境的问题，并提供清晰的选择项供用户作答（二选一或三选一），
          也可以提示用户可以给出自己想到的其他回应。
   - "x"：在问题后用一句话，鼓励用户描述当时的具体细节或感受。
   切记：不要罗列多个并列问题让用户不知该答哪个。

3. 【具体情境，而非空泛抽象】
   问题必须包含一个具体、能让人联想到自身经历的场景（一个具体场合 / 具体动作 / 具体时刻），
   让用户一读就想到"对，我就是这样的人"。
   ✅ 好：周五下班，同事临时拉你去一个十几人的聚餐，你的第一反应是期待，还是想找个借口推掉？
        当时心里是怎么盘算的？
   ❌ 差：你周末更喜欢和朋友聚会还是独自待着？为什么？（太抽象、太宽泛，用户无从想起细节）

4. 【简洁 ≠ 简单】
   - 简洁：用尽量短的句子把情境讲清楚，不要啰嗦铺垫、不要堆砌形容词。
   - 不简单：情境要有信息量、有代入感。禁止"你喜欢社交吗？""你常焦虑吗？"这种一句话空洞问题。

5. 【避免重复】
   结合上方完整历史对话，不要问与之前高度相似的问题，请换一个新角度切入同一维度。

【输出格式】
只返回 JSON，不要有任何额外文字：
{"question": "[共情回应上一句] + [过渡] + [具体情境问题+选择项] + [鼓励描述细节]"}"""

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
    current_ocean: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    生成探索性问题
    
    这是问题生成器的核心函数，负责：
    1. 获取维度信息
    2. 构建 Prompt
    3. 调用 LLM
    4. 解析结果
    5. 处理错误和 fallback
    
    参数:
        dimension_id: 维度ID（如 "social"）
        history: 最近2轮对话历史，格式为 [{"question": "...", "answer": "..."}, ...]
        current_ocean: 当前 OCEAN 分数，格式为 {"O": 0.5, "C": 0.5, ...}
    
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
        examples=examples
    )
    
    # 构建消息列表
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # 调用 LLM
    try:
        # 调用 chat 方法，指定功能类型为问题生成
        response = chat(
            messages=messages,
            function="question_generation"
        )
        
        # 解析结果
        question = parse_question_response(response)
        
        # 如果解析成功，返回 AI 生成的问题
        if question:
            return {"question": question}
        
        # 解析失败，使用 fallback
        fallback_question = dimension.get_random_question()
        return {"question": fallback_question}
        
    except Exception as e:
        # LLM 调用失败（网络错误、API错误等），使用 fallback
        fallback_question = dimension.get_random_question()
        return {"question": fallback_question}


# ============================================================================
# 维度选择策略（供 Agent 模块使用）
# ============================================================================

def select_next_dimension(
    dimension_uncertainty: Dict[str, float],
    exploration_counts: Dict[str, int]
) -> str:
    """
    选择下一个要探索的维度
    
    维度选择策略（方案B）：
    1. 有高不确定性维度（> 0.3）？ → 选择不确定性最高的
    2. 有探索次数少的维度（< 2次）？ → 选择探索次数最少的
    3. 随机选择一个维度
    
    此函数供 Agent 模块调用，用于决定下一个问题应该探索哪个维度。
    
    参数:
        dimension_uncertainty: 各维度的不确定性，格式为 {"social": 0.4, "emotion": 0.2, ...}
        exploration_counts: 各维度的探索次数，格式为 {"social": 1, "emotion": 3, ...}
    
    返回:
        选定的维度ID
    """
    from .modules import get_all_dimension_ids
    
    # 获取所有维度ID
    all_dimensions = get_all_dimension_ids()
    
    # 步骤1：检查高不确定性维度
    high_uncertainty_dims = []
    for dim_id in all_dimensions:
        uncertainty = dimension_uncertainty.get(dim_id, 0.5)  # 默认不确定性为0.5
        if uncertainty > UNCERTAINTY_THRESHOLD:
            high_uncertainty_dims.append((dim_id, uncertainty))
    
    # 如果有高不确定性维度，选择不确定性最高的
    if high_uncertainty_dims:
        # 按不确定性降序排序
        high_uncertainty_dims.sort(key=lambda x: x[1], reverse=True)
        return high_uncertainty_dims[0][0]
    
    # 步骤2：检查探索次数少的维度
    low_exploration_dims = []
    for dim_id in all_dimensions:
        count = exploration_counts.get(dim_id, 0)  # 默认探索次数为0
        if count < MIN_EXPLORATION_COUNT:
            low_exploration_dims.append((dim_id, count))
    
    # 如果有探索次数少的维度，选择探索次数最少的
    if low_exploration_dims:
        # 按探索次数升序排序
        low_exploration_dims.sort(key=lambda x: x[1])
        return low_exploration_dims[0][0]
    
    # 步骤3：所有维度都满足条件，随机选择一个
    return random.choice(all_dimensions)