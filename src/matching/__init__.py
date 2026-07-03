"""
人物匹配模块

本模块负责将用户的人格向量与人物库中的人物进行匹配，
找到最相似的历史/文学/影视人物。

主要功能：
1. 人物数据结构定义
2. 余弦相似度计算
3. 匹配逻辑
4. 热度等级计算
5. 付费内容判断

使用示例：
    from src.matching import match_character, get_best_match
    
    # 用户 OCEAN 分数
    user_ocean = {"O": 0.72, "C": 0.65, "E": 0.45, "A": 0.58, "N": 0.32}
    
    # 匹配人物
    result = get_best_match(user_ocean, characters)
"""

# 导入人物数据结构
from .matcher import CharacterData, MatchResult

# 导入相似度计算函数
from .matcher import cosine_similarity, calculate_ocean_similarity

# 导入匹配函数
from .matcher import match_character, get_best_match

# 导入热度计算函数
from .matcher import calculate_heat_level, HEAT_LEVELS

# 导入结果创建函数
from .matcher import create_match_result

# 导入验证函数
from .matcher import validate_source, validate_era_for_history

# 导入常量
from .matcher import SOURCE_TYPES, FREE_FIELDS, PAID_FIELDS


# ============================================================
# 模块级别的便捷函数
# ============================================================

def get_heat_level_name(match_count: int, total_characters: int, all_match_counts: List[int]) -> str:
    """
    获取热度等级名称（便捷函数）
    
    参数:
        match_count: 该人物的匹配次数
        total_characters: 人物库总人数
        all_match_counts: 所有人物的匹配次数列表
    
    返回:
        热度等级名称
    """
    level_name, _ = calculate_heat_level(match_count, total_characters, all_match_counts)
    return level_name


def get_heat_percent(match_count: int, total_characters: int, all_match_counts: List[int]) -> int:
    """
    获取热度百分比排名（便捷函数）
    
    参数:
        match_count: 该人物的匹配次数
        total_characters: 人物库总人数
        all_match_counts: 所有人物的匹配次数列表
    
    返回:
        百分比排名（0-100）
    """
    _, percent = calculate_heat_level(match_count, total_characters, all_match_counts)
    return percent


# 导入类型
from typing import List


# ============================================================
# 模块信息
# ============================================================

__all__ = [
    # 数据结构
    "CharacterData",
    "MatchResult",
    
    # 相似度计算
    "cosine_similarity",
    "calculate_ocean_similarity",
    
    # 匹配函数
    "match_character",
    "get_best_match",
    
    # 热度计算
    "calculate_heat_level",
    "get_heat_level_name",
    "get_heat_percent",
    "HEAT_LEVELS",
    
    # 结果创建
    "create_match_result",
    
    # 验证函数
    "validate_source",
    "validate_era_for_history",
    
    # 常量
    "SOURCE_TYPES",
    "FREE_FIELDS",
    "PAID_FIELDS",
]