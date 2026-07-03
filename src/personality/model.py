"""
人格向量数据结构定义

本文件定义了人格向量的数据结构，包括：
- OCEANVector:OCEAN 五维人格向量
- Dimension11Vector:11 维问题维度向量

这些数据结构用于：
1. 存储用户的人格状态
2. 记录人格向量的变化过程
3. 支持序列化和反序列化
4. 提供辅助方法用于分析和展示
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from datetime import datetime
import json

# 导入 OCEAN 维度定义
from .ocean import (
    OCEAN_DIMENSIONS,
    OCEAN_CHINESE_NAMES,
    validate_score,
    get_score_level
)

# ============================================================
# 11 维问题维度定义
# ============================================================

# 11 个问题维度的 ID（短名，与 src/questions/modules/ 中的维度 ID 保持一致）
DIMENSION11_NAMES = [
    "social",        # 社交互动
    "emotion",       # 情绪体验
    "decision",      # 决策风格
    "values",        # 价值取向
    "self_awareness",  # 自我认知
    "trust",         # 人际信任
    "stress",        # 压力应对
    "creativity",    # 创造探索
    "intimacy",      # 亲密关系
    "achievement",   # 成就动机
    "life_attitude"  # 生活态度
]

# 11 个问题维度的中文名称
DIMENSION11_CHINESE_NAMES = {
    "social": "社交互动",
    "emotion": "情绪体验",
    "decision": "决策风格",
    "values": "价值取向",
    "self_awareness": "自我认知",
    "trust": "人际信任",
    "stress": "压力应对",
    "creativity": "创造探索",
    "intimacy": "亲密关系",
    "achievement": "成就动机",
    "life_attitude": "生活态度"
}

# 11 维与 OCEAN 的映射关系
DIMENSION11_TO_OCEAN_MAPPING = {
    "social": ["E"],                  # 社交互动 → 外向性
    "emotion": ["N"],                 # 情绪体验 → 神经质
    "decision": ["C", "O"],           # 决策风格 → 责任心、开放性
    "values": ["O", "A"],             # 价值取向 → 开放性、宜人性
    "self_awareness": ["N"],          # 自我认知 → 神经质
    "trust": ["A"],                   # 人际信任 → 宜人性
    "stress": ["N", "C"],             # 压力应对 → 神经质、责任心
    "creativity": ["O"],              # 创造探索 → 开放性
    "intimacy": ["A", "N"],           # 亲密关系 → 宜人性、神经质
    "achievement": ["C"],             # 成就动机 → 责任心
    "life_attitude": ["N", "E"]       # 生活态度 → 神经质、外向性
}


# ============================================================
# OCEAN 五维人格向量类
# ============================================================

@dataclass
class OCEANVector:
    """
    OCEAN 五维人格向量
    
    存储用户在 OCEAN 五个维度上的分数和不确定性。
    分数范围:0.0 ~ 1.0
    精度:0.01
    """
    
    # ---------- 五个维度的分数 ----------
    openness: float = 0.5              # O - 开放性，默认 0.5（中等）
    conscientiousness: float = 0.5    # C - 责任心，默认 0.5（中等）
    extraversion: float = 0.5         # E - 外向性，默认 0.5（中等）
    agreeableness: float = 0.5        # A - 宜人性，默认 0.5（中等）
    neuroticism: float = 0.5          # N - 神经质，默认 0.5（中等）
    
    # ---------- 五个维度的不确定性 ----------
    # 不确定性范围：0.0（完全确定）~ 1.0（完全不确定）
    openness_uncertainty: float = 1.0              # 开放性的不确定性，默认 1.0（完全不确定）
    conscientiousness_uncertainty: float = 1.0     # 责任心的不确定性
    extraversion_uncertainty: float = 1.0          # 外向性的不确定性
    agreeableness_uncertainty: float = 1.0         # 宜人性的不确定性
    neuroticism_uncertainty: float = 1.0           # 神经质的不确定性
    
    # ---------- 元数据 ----------
    created_at: datetime = field(default_factory=datetime.now)   # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)   # 最后更新时间
    update_count: int = 0                                        # 更新次数
    
    def __post_init__(self):
        """
        初始化后验证分数范围
        """
        # 验证所有分数是否在有效范围内
        self._validate_all_scores()
    
    def _validate_all_scores(self):
        """
        验证所有分数是否在有效范围内（0.0 ~ 1.0）
        """
        # 获取所有分数字段
        scores = [
            self.openness, self.conscientiousness, self.extraversion,
            self.agreeableness, self.neuroticism
        ]
        
        # 验证每个分数
        for score in scores:
            if not validate_score(score):
                raise ValueError(f"分数必须在 0.0 到 1.0 之间，当前值: {score}")
        
        # 验证不确定性
        uncertainties = [
            self.openness_uncertainty, self.conscientiousness_uncertainty,
            self.extraversion_uncertainty, self.agreeableness_uncertainty,
            self.neuroticism_uncertainty
        ]
        
        for uncertainty in uncertainties:
            if not validate_score(uncertainty):
                raise ValueError(f"不确定性必须在 0.0 到 1.0 之间，当前值: {uncertainty}")
    
    def to_vector(self) -> List[float]:
        """
        将 OCEAN 向量转换为数值列表
        
        返回:
            包含五个维度分数的列表 [O, C, E, A, N]
        """
        return [
            self.openness,           # 开放性
            self.conscientiousness,  # 责任心
            self.extraversion,       # 外向性
            self.agreeableness,      # 宜人性
            self.neuroticism         # 神经质
        ]
    
    def to_uncertainty_vector(self) -> List[float]:
        """
        将不确定性转换为数值列表
        
        返回:
            包含五个维度不确定性的列表
        """
        return [
            self.openness_uncertainty,           # 开放性的不确定性
            self.conscientiousness_uncertainty,  # 责任心的不确定性
            self.extraversion_uncertainty,       # 外向性的不确定性
            self.agreeableness_uncertainty,      # 宜人性的不确定性
            self.neuroticism_uncertainty         # 神经质的不确定性
        ]
    
    def get_average_uncertainty(self) -> float:
        """
        计算平均不确定性
        
        返回:
            五个维度不确定性的平均值
        """
        uncertainties = self.to_uncertainty_vector()
        return sum(uncertainties) / len(uncertainties)
    
    def get_dominant_traits(self, top_n: int = 2) -> List[Tuple[str, float]]:
        """
        获取主导特质（分数最高的 N 个维度）
        
        参数:
            top_n: 要返回的维度数量，默认 2
        
        返回:
            包含 (维度名称, 分数) 元组的列表，按分数降序排列
        """
        # 构建维度名称和分数的列表
        traits = [
            (OCEAN_CHINESE_NAMES["O"], self.openness),
            (OCEAN_CHINESE_NAMES["C"], self.conscientiousness),
            (OCEAN_CHINESE_NAMES["E"], self.extraversion),
            (OCEAN_CHINESE_NAMES["A"], self.agreeableness),
            (OCEAN_CHINESE_NAMES["N"], self.neuroticism)
        ]
        
        # 按分数降序排序
        sorted_traits = sorted(traits, key=lambda x: x[1], reverse=True)
        
        # 返回前 N 个
        return sorted_traits[:top_n]
    
    def get_trait_levels(self) -> Dict[str, str]:
        """
        获取每个维度的等级描述
        
        返回:
            以维度名称为键，等级描述为值的字典
        """
        return {
            OCEAN_CHINESE_NAMES["O"]: get_score_level(self.openness),
            OCEAN_CHINESE_NAMES["C"]: get_score_level(self.conscientiousness),
            OCEAN_CHINESE_NAMES["E"]: get_score_level(self.extraversion),
            OCEAN_CHINESE_NAMES["A"]: get_score_level(self.agreeableness),
            OCEAN_CHINESE_NAMES["N"]: get_score_level(self.neuroticism)
        }
    
    def to_dict(self) -> Dict:
        """
        将 OCEAN 向量序列化为字典
        
        返回:
            包含所有数据的字典，可用于 JSON 序列化
        """
        return {
            "ocean": {
                "openness": self.openness,
                "conscientiousness": self.conscientiousness,
                "extraversion": self.extraversion,
                "agreeableness": self.agreeableness,
                "neuroticism": self.neuroticism
            },
            "uncertainty": {
                "openness": self.openness_uncertainty,
                "conscientiousness": self.conscientiousness_uncertainty,
                "extraversion": self.extraversion_uncertainty,
                "agreeableness": self.agreeableness_uncertainty,
                "neuroticism": self.neuroticism_uncertainty
            },
            "metadata": {
                "created_at": self.created_at.isoformat(),    # 转换为 ISO 格式字符串
                "updated_at": self.updated_at.isoformat(),
                "update_count": self.update_count
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "OCEANVector":
        """
        从字典反序列化 OCEAN 向量
        
        参数:
            data: 包含 OCEAN 向量数据的字典
        
        返回:
            OCEANVector 实例
        """
        return cls(
            openness=data["ocean"]["openness"],
            conscientiousness=data["ocean"]["conscientiousness"],
            extraversion=data["ocean"]["extraversion"],
            agreeableness=data["ocean"]["agreeableness"],
            neuroticism=data["ocean"]["neuroticism"],
            openness_uncertainty=data["uncertainty"]["openness"],
            conscientiousness_uncertainty=data["uncertainty"]["conscientiousness"],
            extraversion_uncertainty=data["uncertainty"]["extraversion"],
            agreeableness_uncertainty=data["uncertainty"]["agreeableness"],
            neuroticism_uncertainty=data["uncertainty"]["neuroticism"],
            created_at=datetime.fromisoformat(data["metadata"]["created_at"]),
            updated_at=datetime.fromisoformat(data["metadata"]["updated_at"]),
            update_count=data["metadata"]["update_count"]
        )
    
    def update_dimension(self, dimension: str, delta: float, uncertainty_reduction: float = 0.1):
        """
        更新指定维度的分数和不确定性
        
        参数:
            dimension: 维度缩写(O/C/E/A/N)
            delta: 分数变化量(可正可负)
            uncertainty_reduction: 不确定性减少量(默认 0.1)
        """
        # 维度名称到属性的映射
        dimension_map = {
            "O": ("openness", "openness_uncertainty"),
            "C": ("conscientiousness", "conscientiousness_uncertainty"),
            "E": ("extraversion", "extraversion_uncertainty"),
            "A": ("agreeableness", "agreeableness_uncertainty"),
            "N": ("neuroticism", "neuroticism_uncertainty")
        }
        
        # 验证维度是否有效
        if dimension not in dimension_map:
            raise ValueError(f"无效的维度: {dimension}")
        
        # 获取对应的属性名
        score_attr, uncertainty_attr = dimension_map[dimension]
        
        # 更新分数（限制在 0.0 ~ 1.0 范围内）
        current_score = getattr(self, score_attr)
        new_score = max(0.0, min(1.0, current_score + delta))
        setattr(self, score_attr, new_score)
        
        # 更新不确定性（减少，但不低于 0.0）
        current_uncertainty = getattr(self, uncertainty_attr)
        new_uncertainty = max(0.0, current_uncertainty - uncertainty_reduction)
        setattr(self, uncertainty_attr, new_uncertainty)
        
        # 更新元数据
        self.updated_at = datetime.now()
        self.update_count += 1


# ============================================================
# 11 维问题维度向量类
# ============================================================

@dataclass
class Dimension11Vector:
    """
    11 维问题维度向量
    
    存储用户在 11 个问题维度上的分数、不确定性和探索次数。
    用于问题生成和辅助匹配。
    """
    
    # ---------- 11 个维度的分数 ----------
    social: float = 0.5            # 社交互动
    emotion: float = 0.5           # 情绪体验
    decision: float = 0.5          # 决策风格
    values: float = 0.5            # 价值取向
    self_awareness: float = 0.5    # 自我认知
    trust: float = 0.5             # 人际信任
    stress: float = 0.5            # 压力应对
    creativity: float = 0.5        # 创造探索
    intimacy: float = 0.5          # 亲密关系
    achievement: float = 0.5       # 成就动机
    life_attitude: float = 0.5     # 生活态度

    # ---------- 11 个维度的不确定性 ----------
    social_uncertainty: float = 1.0
    emotion_uncertainty: float = 1.0
    decision_uncertainty: float = 1.0
    values_uncertainty: float = 1.0
    self_awareness_uncertainty: float = 1.0
    trust_uncertainty: float = 1.0
    stress_uncertainty: float = 1.0
    creativity_uncertainty: float = 1.0
    intimacy_uncertainty: float = 1.0
    achievement_uncertainty: float = 1.0
    life_attitude_uncertainty: float = 1.0

    # ---------- 11 个维度的探索次数 ----------
    social_explore_count: int = 0
    emotion_explore_count: int = 0
    decision_explore_count: int = 0
    values_explore_count: int = 0
    self_awareness_explore_count: int = 0
    trust_explore_count: int = 0
    stress_explore_count: int = 0
    creativity_explore_count: int = 0
    intimacy_explore_count: int = 0
    achievement_explore_count: int = 0
    life_attitude_explore_count: int = 0
    
    # ---------- 元数据 ----------
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_vector(self) -> List[float]:
        """
        将 11 维向量转换为数值列表
        
        返回:
            包含 11 个维度分数的列表
        """
        return [
            self.social,
            self.emotion,
            self.decision,
            self.values,
            self.self_awareness,
            self.trust,
            self.stress,
            self.creativity,
            self.intimacy,
            self.achievement,
            self.life_attitude
        ]
    
    def to_uncertainty_vector(self) -> List[float]:
        """
        将不确定性转换为数值列表
        
        返回:
            包含 11 个维度不确定性的列表
        """
        return [
            self.social_uncertainty,
            self.emotion_uncertainty,
            self.decision_uncertainty,
            self.values_uncertainty,
            self.self_awareness_uncertainty,
            self.trust_uncertainty,
            self.stress_uncertainty,
            self.creativity_uncertainty,
            self.intimacy_uncertainty,
            self.achievement_uncertainty,
            self.life_attitude_uncertainty
        ]
    
    def to_explore_count_vector(self) -> List[int]:
        """
        将探索次数转换为数值列表
        
        返回:
            包含 11 个维度探索次数的列表
        """
        return [
            self.social_explore_count,
            self.emotion_explore_count,
            self.decision_explore_count,
            self.values_explore_count,
            self.self_awareness_explore_count,
            self.trust_explore_count,
            self.stress_explore_count,
            self.creativity_explore_count,
            self.intimacy_explore_count,
            self.achievement_explore_count,
            self.life_attitude_explore_count
        ]
    
    def get_average_uncertainty(self) -> float:
        """
        计算平均不确定性
        
        返回:
            11 个维度不确定性的平均值
        """
        uncertainties = self.to_uncertainty_vector()
        return sum(uncertainties) / len(uncertainties)
    
    def get_min_explore_count(self) -> int:
        """
        获取最小的探索次数
        
        返回:
            11 个维度中最小的探索次数
        """
        explore_counts = self.to_explore_count_vector()
        return min(explore_counts)
    
    def get_high_uncertainty_dimensions(self, threshold: float = 0.5) -> List[str]:
        """
        获取高不确定性的维度列表
        
        参数:
            threshold: 不确定性阈值，默认 0.5
        
        返回:
            不确定性超过阈值的维度名称列表
        """
        # 维度名称和不确定性的列表
        dimensions_with_uncertainty = list(zip(DIMENSION11_NAMES, self.to_uncertainty_vector()))
        
        # 筛选高不确定性的维度
        high_uncertainty = [
            name for name, uncertainty in dimensions_with_uncertainty 
            if uncertainty > threshold
        ]
        
        return high_uncertainty
    
    def get_unexplored_dimensions(self, min_explore: int = 2) -> List[str]:
        """
        获取探索次数不足的维度列表
        
        参数:
            min_explore: 最小探索次数，默认 2
        
        返回:
            探索次数小于 min_explore 的维度名称列表
        """
        # 维度名称和探索次数的列表
        dimensions_with_count = list(zip(DIMENSION11_NAMES, self.to_explore_count_vector()))
        
        # 筛选探索不足的维度
        unexplored = [
            name for name, count in dimensions_with_count 
            if count < min_explore
        ]
        
        return unexplored
    
    def to_dict(self) -> Dict:
        """
        将 11 维向量序列化为字典
        
        返回:
            包含所有数据的字典
        """
        return {
            "scores": {
                name: getattr(self, name)
                for name in DIMENSION11_NAMES
            },
            "uncertainty": {
                f"{name}_uncertainty": getattr(self, f"{name}_uncertainty")
                for name in DIMENSION11_NAMES
            },
            "explore_count": {
                f"{name}_explore_count": getattr(self, f"{name}_explore_count")
                for name in DIMENSION11_NAMES
            },
            "metadata": {
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Dimension11Vector":
        """
        从字典反序列化 11 维向量
        
        参数:
            data: 包含 11 维向量数据的字典
        
        返回:
            Dimension11Vector 实例
        """
        # 构建参数字典
        kwargs = {}
        
        # 添加分数
        for name in DIMENSION11_NAMES:
            kwargs[name] = data["scores"][name]
        
        # 添加不确定性
        for name in DIMENSION11_NAMES:
            kwargs[f"{name}_uncertainty"] = data["uncertainty"][f"{name}_uncertainty"]
        
        # 添加探索次数
        for name in DIMENSION11_NAMES:
            kwargs[f"{name}_explore_count"] = data["explore_count"][f"{name}_explore_count"]
        
        # 添加元数据
        kwargs["created_at"] = datetime.fromisoformat(data["metadata"]["created_at"])
        kwargs["updated_at"] = datetime.fromisoformat(data["metadata"]["updated_at"])
        
        return cls(**kwargs)
    
    def update_dimension(self, dimension: str, delta: float, uncertainty_reduction: float = 0.1):
        """
        更新指定维度的分数、不确定性和探索次数
        
        参数:
            dimension: 维度名称
            delta: 分数变化量
            uncertainty_reduction: 不确定性减少量
        """
        # 验证维度是否有效
        if dimension not in DIMENSION11_NAMES:
            raise ValueError(f"无效的维度: {dimension}")
        
        # 更新分数
        current_score = getattr(self, dimension)
        new_score = max(0.0, min(1.0, current_score + delta))
        setattr(self, dimension, new_score)
        
        # 更新不确定性
        uncertainty_attr = f"{dimension}_uncertainty"
        current_uncertainty = getattr(self, uncertainty_attr)
        new_uncertainty = max(0.0, current_uncertainty - uncertainty_reduction)
        setattr(self, uncertainty_attr, new_uncertainty)
        
        # 更新探索次数
        explore_count_attr = f"{dimension}_explore_count"
        current_count = getattr(self, explore_count_attr)
        setattr(self, explore_count_attr, current_count + 1)
        
        # 更新时间
        self.updated_at = datetime.now()
