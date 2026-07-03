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
    
    system prompt 定义 AI 的角色、目标和基本规则，在每次调用时保持不变。
    
    返回:
        system prompt 文本
    """
    return """你是一个基于OCEAN人格模型的人格探索专家。你的目标是通过自然对话，逐步了解用户在五个核心人格维度上的特质：

- O（开放性）：好奇心、创造力、接受新事物
- C（责任心）：自律、计划性、目标导向
- E（外向性）：社交活跃度、能量来源
- A（宜人性）：合作性、同理心、信任他人
- N（神经质）：情绪稳定性、焦虑敏感度

你的任务是生成一个探索性问题，帮助了解用户的人格特质。"""


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
        history: 最近2轮对话历史（问题+回答）
        current_ocean: 当前 OCEAN 分数（可选，用于参考）
        examples: 问题示例列表（8个经典问题）
    
    返回:
        user prompt 文本
    """
    # 构建维度信息部分
    dimension_info = f"""【当前探索维度】
维度名称：{dimension.name}
维度描述：{dimension.description}
主要影响的OCEAN维度：{dimension.get_ocean_mapping_description()}
注：用户回答可能同时影响多个OCEAN维度，请根据回答内容综合判断"""
    
    # 构建历史对话部分（如果有）
    history_info = ""
    if history:
        history_lines = []
        for i, h in enumerate(history):
            question = h.get("question", "")
            answer = h.get("answer", "")
            history_lines.append(f"问题：{question}")
            history_lines.append(f"回答：{answer}")
        history_info = f"""【历史对话】
{chr(10).join(history_lines)}"""
    
    # 构建输出要求部分
    output_requirements = """【输出要求】
1. 请生成一个关于当前维度的问题
2. 采用"1+x"模式：先问一个可以准确回答的问题，再加一个开放性问题让用户自由发挥
3. 如果维度跨度较大，请用过渡句自然过渡，让对话感觉连贯
4. 问题要具体、有引导性，让用户愿意分享
5. 输出JSON格式：{"question": "你的问题"}"""
    
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
    
    # 只保留最近2轮对话（4条消息）
    # 每轮对话包含1个问题和1个回答
    recent_history = history[-4:] if len(history) > 4 else history
    
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