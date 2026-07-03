"""
人格向量更新器

本文件定义了人格向量的更新算法，包括：
- 贝叶斯更新算法
- 指数加权移动平均(EWMA)更新算法
- AI 动态判断接口
- 平滑更新逻辑

这些算法用于：
1. 根据用户回答更新人格向量
2. 平滑处理避免剧烈变化
3. 降低不确定性
"""

from typing import Dict, Optional, Tuple
from datetime import datetime

# 导入人格向量类
from .model import OCEANVector, Dimension11Vector, DIMENSION11_TO_OCEAN_MAPPING

# ============================================================
# 更新器配置参数
# ============================================================

# EWMA 学习率（控制新数据对结果的影响程度）
# 值越大，新数据影响越大；值越小，历史数据权重越高
EWMA_LEARNING_RATE = 0.2

# 单次最大变化幅度（限制单次更新的最大变化）
MAX_CHANGE_PER_UPDATE = 0.05

# 最小更新阈值（小于此值的变化不更新）
MIN_UPDATE_THRESHOLD = 0.01

# 不确定性减少量（每次更新减少的不确定性）
UNCERTAINTY_REDUCTION = 0.1

# 贝叶斯先验方差（初始不确定性）
BAYESIAN_PRIOR_VARIANCE = 0.25


# ============================================================
# 人格向量更新器类
# ============================================================

class PersonalityUpdater:
    """
    人格向量更新器
    
    使用贝叶斯更新和 EWMA 算法来平滑更新人格向量。
    支持 AI 动态判断影响值。
    """
    
    def __init__(
        self,
        learning_rate: float = EWMA_LEARNING_RATE,
        max_change: float = MAX_CHANGE_PER_UPDATE,
        min_threshold: float = MIN_UPDATE_THRESHOLD,
        uncertainty_reduction: float = UNCERTAINTY_REDUCTION
    ):
        """
        初始化更新器
        
        参数:
            learning_rate: EWMA 学习率，默认 0.2
            max_change: 单次最大变化幅度，默认 0.05
            min_threshold: 最小更新阈值，默认 0.01
            uncertainty_reduction: 不确定性减少量，默认 0.1
        """
        self.learning_rate = learning_rate           # 学习率
        self.max_change = max_change                  # 最大变化幅度
        self.min_threshold = min_threshold            # 最小更新阈值
        self.uncertainty_reduction = uncertainty_reduction  # 不确定性减少量
    
    # ============================================================
    # EWMA 更新算法
    # ============================================================
    
    def apply_ewma(self, current_value: float, new_value: float) -> float:
        """
        应用指数加权移动平均算法
        
        公式：新值 = α × 新数据 + (1-α) × 历史值
        
        参数:
            current_value: 当前值（历史值）
            new_value: 新数据值
        
        返回:
            更新后的值
        """
        # 计算 EWMA 更新值
        updated_value = self.learning_rate * new_value + (1 - self.learning_rate) * current_value
        
        return updated_value
    
    # ============================================================
    # 贝叶斯更新算法
    # ============================================================
    
    def apply_bayesian(
        self,
        current_value: float,
        current_uncertainty: float,
        observation: float,
        observation_variance: float = 0.1
    ) -> Tuple[float, float]:
        """
        应用贝叶斯更新算法
        
        根据新的观测值更新当前值和不确定性。
        
        参数:
            current_value: 当前值
            current_uncertainty: 当前不确定性
            observation: 观测值（AI 判断的影响值）
            observation_variance: 观测方差，默认 0.1
        
        返回:
            (更新后的值, 更新后的不确定性)
        """
        # 将不确定性转换为方差
        current_variance = current_uncertainty * BAYESIAN_PRIOR_VARIANCE
        
        # 计算卡尔曼增益（决定新观测的权重）
        # K = 当前方差 / (当前方差 + 观测方差)
        kalman_gain = current_variance / (current_variance + observation_variance)
        
        # 更新值：当前值 + 卡尔曼增益 × (观测值 - 当前值)
        updated_value = current_value + kalman_gain * (observation - current_value)
        
        # 更新方差：当前方差 × (1 - 卡尔曼增益)
        updated_variance = current_variance * (1 - kalman_gain)
        
        # 将方差转换回不确定性
        updated_uncertainty = updated_variance / BAYESIAN_PRIOR_VARIANCE
        
        return updated_value, updated_uncertainty
    
    # ============================================================
    # 平滑更新逻辑
    # ============================================================
    
    def smooth_update(
        self,
        current_value: float,
        delta: float
    ) -> float:
        """
        平滑更新，限制变化幅度
        
        参数:
            current_value: 当前值
            delta: 变化量
        
        返回:
            更新后的值
        """
        # 如果变化量太小，不更新
        if abs(delta) < self.min_threshold:
            return current_value
        
        # 限制变化幅度
        if delta > self.max_change:
            delta = self.max_change
        elif delta < -self.max_change:
            delta = -self.max_change
        
        # 计算新值，限制在 0.0 ~ 1.0 范围内
        new_value = current_value + delta
        new_value = max(0.0, min(1.0, new_value))
        
        return new_value
    
    # ============================================================
    # AI 动态判断接口
    # ============================================================
    
    def parse_ai_judgment(self, ai_response: Dict) -> Dict[str, float]:
        """
        解析 AI 动态判断结果
        
        AI 返回的格式示例：
        {
            "O": 0.02,
            "C": 0,
            "E": -0.08,
            "A": 0.01,
            "N": 0
        }
        
        参数:
            ai_response: AI 返回的判断结果字典
        
        返回:
            以维度为键，变化量为值的字典
        """
        # 验证返回格式
        valid_dimensions = ["O", "C", "E", "A", "N"]
        
        # 初始化结果字典
        delta_dict = {}
        
        # 遍历每个维度
        for dim in valid_dimensions:
            # 获取变化量，默认为 0
            delta = ai_response.get(dim, 0.0)
            
            # 验证变化量范围
            if not isinstance(delta, (int, float)):
                delta = 0.0
            
            # 限制变化量范围
            delta = max(-self.max_change, min(self.max_change, delta))
            
            delta_dict[dim] = delta
        
        return delta_dict
    
    # ============================================================
    # 更新 OCEAN 向量
    # ============================================================
    
    def update_ocean(
        self,
        ocean_vector: OCEANVector,
        ai_judgment: Dict[str, float],
        method: str = "ewma"
    ) -> OCEANVector:
        """
        根据 AI 判断更新 OCEAN 向量
        
        参数:
            ocean_vector: 当前的 OCEAN 向量
            ai_judgment: AI 判断的变化量字典，如 {"O": 0.02, "E": -0.08}
            method: 更新方法，"ewma" 或 "bayesian"
        
        返回:
            更新后的 OCEAN 向量
        """
        # 解析 AI 判断结果
        delta_dict = self.parse_ai_judgment(ai_judgment)
        
        # 维度名称到属性的映射
        dimension_map = {
            "O": ("openness", "openness_uncertainty"),
            "C": ("conscientiousness", "conscientiousness_uncertainty"),
            "E": ("extraversion", "extraversion_uncertainty"),
            "A": ("agreeableness", "agreeableness_uncertainty"),
            "N": ("neuroticism", "neuroticism_uncertainty")
        }
        
        # 遍历每个维度进行更新
        for dim, delta in delta_dict.items():
            # 获取属性名
            score_attr, uncertainty_attr = dimension_map[dim]
            
            # 获取当前值
            current_score = getattr(ocean_vector, score_attr)
            current_uncertainty = getattr(ocean_vector, uncertainty_attr)
            
            # 根据方法选择更新算法
            if method == "bayesian":
                # 贝叶斯更新
                new_score, new_uncertainty = self.apply_bayesian(
                    current_score,
                    current_uncertainty,
                    current_score + delta  # 观测值 = 当前值 + 变化量
                )
            else:
                # EWMA 更新（默认）
                new_score = self.smooth_update(current_score, delta)
                new_uncertainty = max(0.0, current_uncertainty - self.uncertainty_reduction)
            
            # 更新向量
            setattr(ocean_vector, score_attr, new_score)
            setattr(ocean_vector, uncertainty_attr, new_uncertainty)
        
        # 更新元数据
        ocean_vector.updated_at = datetime.now()
        ocean_vector.update_count += 1
        
        return ocean_vector
    
    # ============================================================
    # 更新 11 维向量
    # ============================================================
    
    def update_dimension11(
        self,
        dim11_vector: Dimension11Vector,
        dimension: str,
        delta: float
    ) -> Dimension11Vector:
        """
        更新 11 维问题维度向量
        
        参数:
            dim11_vector: 当前的 11 维向量
            dimension: 要更新的维度名称
            delta: 变化量
        
        返回:
            更新后的 11 维向量
        """
        # 更新指定维度
        dim11_vector.update_dimension(
            dimension=dimension,
            delta=delta,
            uncertainty_reduction=self.uncertainty_reduction
        )
        
        return dim11_vector
    
    # ============================================================
    # 从 11 维更新 OCEAN
    # ============================================================
    
    def update_ocean_from_dimension11(
        self,
        ocean_vector: OCEANVector,
        dim11_vector: Dimension11Vector,
        dimension: str,
        delta: float
    ) -> Tuple[OCEANVector, Dimension11Vector]:
        """
        从 11 维更新 OCEAN 向量
        
        根据 11 维与 OCEAN 的映射关系，更新对应的 OCEAN 维度。
        
        参数:
            ocean_vector: 当前的 OCEAN 向量
            dim11_vector: 当前的 11 维向量
            dimension: 11 维维度名称
            delta: 变化量
        
        返回:
            (更新后的 OCEAN 向量, 更新后的 11 维向量)
        """
        # 更新 11 维向量
        dim11_vector = self.update_dimension11(dim11_vector, dimension, delta)
        
        # 获取该维度对应的 OCEAN 维度
        ocean_dimensions = DIMENSION11_TO_OCEAN_MAPPING.get(dimension, [])
        
        # 如果该维度影响多个 OCEAN 维度，平均分配影响
        if ocean_dimensions:
            # 计算每个 OCEAN 维度的变化量
            delta_per_dimension = delta / len(ocean_dimensions)
            
            # 构建 AI 判断字典
            ai_judgment = {dim: 0.0 for dim in ["O", "C", "E", "A", "N"]}
            for ocean_dim in ocean_dimensions:
                ai_judgment[ocean_dim] = delta_per_dimension
            
            # 更新 OCEAN 向量
            ocean_vector = self.update_ocean(ocean_vector, ai_judgment)
        
        return ocean_vector, dim11_vector
    
    # ============================================================
    # 收敛判断
    # ============================================================
    
    def check_convergence(
        self,
        ocean_vector: OCEANVector,
        dim11_vector: Dimension11Vector,
        min_rounds: int = 15,
        min_explore_per_dimension: int = 2,
        max_uncertainty: float = 0.3
    ) -> Tuple[bool, Dict]:
        """
        检查人格向量是否收敛
        
        收敛条件：
        1. 最小对话轮次 ≥ min_rounds
        2. 每个维度至少被探索 min_explore_per_dimension 次
        3. 所有维度不确定性 < max_uncertainty
        
        参数:
            ocean_vector: OCEAN 向量
            dim11_vector: 11 维向量
            min_rounds: 最小对话轮次
            min_explore_per_dimension: 每个维度最小探索次数
            max_uncertainty: 最大允许的不确定性
        
        返回:
            (是否收敛, 详细信息字典)
        """
        # 初始化检查结果
        checks = {
            "min_rounds": False,
            "dimension_coverage": False,
            "uncertainty": False,
            "details": {}
        }
        
        # 检查 1：最小对话轮次
        total_explores = sum(dim11_vector.to_explore_count_vector())
        checks["min_rounds"] = total_explores >= min_rounds
        checks["details"]["total_rounds"] = total_explores
        
        # 检查 2：维度覆盖率
        min_explore = dim11_vector.get_min_explore_count()
        checks["dimension_coverage"] = min_explore >= min_explore_per_dimension
        checks["details"]["min_explore_count"] = min_explore
        checks["details"]["unexplored_dimensions"] = dim11_vector.get_unexplored_dimensions(min_explore_per_dimension)
        
        # 检查 3：不确定性
        avg_ocean_uncertainty = ocean_vector.get_average_uncertainty()
        avg_dim11_uncertainty = dim11_vector.get_average_uncertainty()
        checks["uncertainty"] = (avg_ocean_uncertainty < max_uncertainty and 
                                  avg_dim11_uncertainty < max_uncertainty)
        checks["details"]["ocean_uncertainty"] = avg_ocean_uncertainty
        checks["details"]["dim11_uncertainty"] = avg_dim11_uncertainty
        checks["details"]["high_uncertainty_dimensions"] = dim11_vector.get_high_uncertainty_dimensions(max_uncertainty)
        
        # 综合判断
        is_converged = checks["min_rounds"] and checks["dimension_coverage"] and checks["uncertainty"]
        
        return is_converged, checks
