"""
问题模块系统

本模块负责生成探索用户人格的问题。
核心功能：
1. 定义 11 个问题维度（探测手段）
2. 生成探索性问题
3. 选择下一个探索维度

设计说明：
- 11 个问题维度是"探测手段"，用于生成问题
- OCEAN 5 维是"存储状态"，用于存储人格向量
- 问题采用"1+x"模式：先问一个可以准确回答的问题，再加一个开放性问题

使用示例：
    from src.questions import generate_question, select_next_dimension
    
    # 选择下一个探索维度
    next_dim = select_next_dimension(
        dimension_uncertainty={"social": 0.4, "emotion": 0.2, ...},
        exploration_counts={"social": 1, "emotion": 3, ...}
    )
    
    # 生成问题
    result = generate_question(
        dimension_id=next_dim,
        history=[{"question": "...", "answer": "..."}],
        current_ocean={"O": 0.5, "C": 0.5, ...}
    )
    
    # 获取问题文本
    question = result["question"]
"""

# 从维度模块导入
from .modules import (
    QuestionDimension,
    ALL_DIMENSIONS,
    DIMENSION_MAP,
    get_dimension_by_id,
    get_all_dimension_ids,
)

# 从生成器模块导入
from .generator import (
    generate_question,
    select_next_dimension,
    build_system_prompt,
    build_user_prompt,
    parse_question_response,
    UNCERTAINTY_THRESHOLD,
    MIN_EXPLORATION_COUNT,
)


# ============================================================================
# 模块级别的便捷函数
# ============================================================================

def get_dimension_info(dimension_id: str) -> Dict:
    """
    获取维度的详细信息
    
    参数:
        dimension_id: 维度ID（如 "social"）
    
    返回:
        包含维度信息的字典
    """
    dim = get_dimension_by_id(dimension_id)
    return {
        "id": dim.id,
        "name": dim.name,
        "description": dim.description,
        "ocean_mapping": dim.ocean_mapping,
        "theory_source": dim.theory_source,
        "questions_count": len(dim.questions)
    }


def list_all_dimensions() -> List[Dict]:
    """
    列出所有维度的基本信息
    
    返回:
        所有维度的基本信息列表
    """
    return [get_dimension_info(dim_id) for dim_id in get_all_dimension_ids()]


# 导入 Dict 和 List 类型用于类型注解
from typing import Dict, List


# ============================================================================
# 模块导出列表
# ============================================================================

__all__ = [
    # 维度相关
    "QuestionDimension",
    "ALL_DIMENSIONS",
    "DIMENSION_MAP",
    "get_dimension_by_id",
    "get_all_dimension_ids",
    "get_dimension_info",
    "list_all_dimensions",
    
    # 问题生成相关
    "generate_question",
    "select_next_dimension",
    "build_system_prompt",
    "build_user_prompt",
    "parse_question_response",
    
    # 常量
    "UNCERTAINTY_THRESHOLD",
    "MIN_EXPLORATION_COUNT",
]