"""
人格建模模块

本模块提供人格向量的定义和更新功能，包括：
- OCEAN 五维人格向量
- 11 维问题维度向量
- 人格向量更新器
"""

# 导出 OCEAN 相关定义
from .ocean import (
    OCEAN_DIMENSIONS,
    OCEAN_FULL_NAMES,
    OCEAN_CHINESE_NAMES,
    OCEAN_DESCRIPTIONS,
    OCEAN_FACETS,
    HIGH_SCORE_TRAITS,
    LOW_SCORE_TRAITS,
    get_dimension_info,
    validate_score,
    get_score_level,
    get_all_dimensions_info
)

# 导出人格向量类
from .model import (
    OCEANVector,
    Dimension11Vector,
    DIMENSION11_NAMES,
    DIMENSION11_CHINESE_NAMES,
    DIMENSION11_TO_OCEAN_MAPPING
)

# 导出更新器类
from .updater import (
    PersonalityUpdater,
    EWMA_LEARNING_RATE,
    MAX_CHANGE_PER_UPDATE,
    MIN_UPDATE_THRESHOLD,
    UNCERTAINTY_REDUCTION
)
