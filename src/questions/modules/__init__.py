"""
问题维度模块

本模块定义了 11 个问题维度，用于探索用户的人格特质。
每个维度包含：维度ID、名称、描述、映射的OCEAN维度、问题示例列表。

问题维度是"探测手段"，用于生成问题；
OCEAN 5维是"存储状态"，用于存储人格向量。
"""

from dataclasses import dataclass
from typing import List


@dataclass
class QuestionDimension:
    """
    问题维度数据结构
    
    属性:
        id: 维度ID（如 "social"）
        name: 维度名称（如 "社交互动"）
        description: 维度描述（说明该维度探索什么内容）
        ocean_mapping: 映射的OCEAN维度列表（如 ["E"] 表示主要影响外向性）
        theory_source: 理论来源（可选，说明该维度的心理学理论基础）
        questions: 问题示例列表（8个经典问题，采用"1+x"模式）
    
    说明:
        - ocean_mapping 只指出主要影响的维度，AI会根据回答内容动态判断所有5个维度的影响
        - questions 是参考示例和fallback备选，AI生成问题时可以参考这些示例的风格和形式
        - "1+x"模式：先问一个可以准确回答的问题，再加一个开放性问题
    """
    id: str
    name: str
    description: str
    ocean_mapping: List[str]
    theory_source: str = ""
    questions: List[str] = None
    
    def __post_init__(self):
        """
        初始化后处理
        
        如果 questions 为 None，则设置为空列表
        """
        if self.questions is None:
            self.questions = []
    
    def get_random_question(self) -> str:
        """
        从问题列表中随机获取一个问题
        
        用于 AI 生成失败时的 fallback
        
        返回:
            随机选择的问题文本
        """
        import random
        if not self.questions:
            return f"请告诉我关于{self.name}的一些想法。"
        return random.choice(self.questions)
    
    def get_ocean_mapping_description(self) -> str:
        """
        获取 OCEAN 映射关系的描述文本
        
        用于构建 Prompt 时告诉 AI 该维度主要影响哪些 OCEAN 维度
        
        返回:
            映射关系描述（如 "E（外向性）"）
        """
        ocean_names = {
            "O": "开放性",
            "C": "责任心",
            "E": "外向性",
            "A": "宜人性",
            "N": "神经质"
        }
        mappings = [f"{dim}（{ocean_names[dim]}）" for dim in self.ocean_mapping]
        return "、".join(mappings)


# 导入所有维度定义
from .social import SOCIAL_DIMENSION
from .emotion import EMOTION_DIMENSION
from .decision import DECISION_DIMENSION
from .values import VALUES_DIMENSION
from .self_awareness import SELF_AWARENESS_DIMENSION
from .trust import TRUST_DIMENSION
from .stress import STRESS_DIMENSION
from .creativity import CREATIVITY_DIMENSION
from .achievement import ACHIEVEMENT_DIMENSION
from .life_attitude import LIFE_ATTITUDE_DIMENSION
from .intimacy import INTIMACY_DIMENSION


# 所有维度列表（共11个维度）
ALL_DIMENSIONS: List[QuestionDimension] = [
    SOCIAL_DIMENSION,
    EMOTION_DIMENSION,
    DECISION_DIMENSION,
    VALUES_DIMENSION,
    SELF_AWARENESS_DIMENSION,
    TRUST_DIMENSION,
    STRESS_DIMENSION,
    CREATIVITY_DIMENSION,
    ACHIEVEMENT_DIMENSION,
    LIFE_ATTITUDE_DIMENSION,
    INTIMACY_DIMENSION,
]


# 维度ID到维度对象的映射字典
DIMENSION_MAP: dict = {dim.id: dim for dim in ALL_DIMENSIONS}


def get_dimension_by_id(dimension_id: str) -> QuestionDimension:
    """
    根据维度ID获取维度对象
    
    参数:
        dimension_id: 维度ID（如 "social"）
    
    返回:
        维度对象
    
    异常:
        KeyError: 如果维度ID不存在
    """
    if dimension_id not in DIMENSION_MAP:
        raise KeyError(f"维度ID '{dimension_id}' 不存在")
    return DIMENSION_MAP[dimension_id]


def get_all_dimension_ids() -> List[str]:
    """
    获取所有维度ID列表
    
    返回:
        所有维度ID的列表
    """
    return list(DIMENSION_MAP.keys())