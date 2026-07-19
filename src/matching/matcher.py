"""
人物匹配模块

本文件负责将用户的人格向量与人物库中的人物进行匹配，
找到最相似的历史/文学/影视人物。

核心功能：
1. 人物数据结构定义
2. 余弦相似度计算
3. 匹配逻辑（返回最相似的人物）
4. 热度等级计算
5. 付费内容判断
"""

import math
import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime


# ============================================================
# 常量定义
# ============================================================

# 热度等级定义（5个等级，每20%一个等级）
HEAT_LEVELS = {
    1: {"name": "最热门", "range": (0, 20)},      # 前20%
    2: {"name": "热门", "range": (20, 40)},       # 20%-40%
    3: {"name": "中等", "range": (40, 60)},       # 40%-60%
    4: {"name": "冷门", "range": (60, 80)},       # 60%-80%
    5: {"name": "最冷门", "range": (80, 100)},    # 后20%
}

# 来源类型定义（当前只支持历史人物，清朝或之前）
SOURCE_TYPES = ["历史"]

# 基础展示字段（免费可见）
FREE_FIELDS = ["name", "source", "era", "image_path", "description", "match_count"]

# 付费解锁字段
PAID_FIELDS = ["tags", "quote", "personality_keyword", "classic_events", 
               "fun_facts", "advice", "related_books"]


# ============================================================
# 人物数据结构
# ============================================================

@dataclass
class CharacterData:
    """
    人物数据类
    
    存储单个人物的所有信息，与数据库 Character 表结构对应。
    """
    # ---------- 基本信息 ----------
    character_id: str                              # 人物唯一标识
    name: str                                      # 人物名称
    source: str                                    # 来源（历史）
    era: str = ""                                  # 年代/时期（历史人物必填）
    description: str = ""                          # 人物简介生平
    
    # ---------- 人格向量 ----------
    ocean_vector: Dict[str, float] = field(default_factory=lambda: {
        "O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5
    })                                             # OCEAN 五维分数
    
    # ---------- 基础展示字段（免费可见） ----------
    image_path: str = ""                           # 人物图片本地路径
    
    # ---------- 付费解锁字段 ----------
    tags: List[str] = field(default_factory=list)  # 标签列表（5个）
    quote: str = ""                                # 语录/名言/成语/评价
    personality_keyword: str = ""                  # 性格关键词
    classic_events: str = ""                       # 经典场景/事件
    fun_facts: str = ""                            # 趣味冷知识
    advice: str = ""                               # 性格建议
    related_books: str = ""                        # 相关书籍
    
    # ---------- 统计和状态 ----------
    match_count: int = 0                           # 匹配次数
    is_active: bool = True                         # 是否可用
    
    # ---------- 时间 ----------
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def get_ocean_list(self) -> List[float]:
        """
        获取 OCEAN 向量的列表形式
        
        返回:
            [O, C, E, A, N] 的列表
        """
        return [
            self.ocean_vector.get("O", 0.5),
            self.ocean_vector.get("C", 0.5),
            self.ocean_vector.get("E", 0.5),
            self.ocean_vector.get("A", 0.5),
            self.ocean_vector.get("N", 0.5)
        ]
    
    def to_dict(self, include_paid: bool = False) -> Dict[str, Any]:
        """
        转换为字典格式
        
        参数:
            include_paid: 是否包含付费字段
        
        返回:
            人物信息的字典
        """
        # 基础字段（始终返回）
        result = {
            "character_id": self.character_id,
            "name": self.name,
            "source": self.source,
            "era": self.era,
            "image_path": self.image_path,
            "description": self.description,
            "match_count": self.match_count,
            "is_paid_locked": True,  # 标记付费字段是否锁定
        }
        
        # 付费字段（根据参数决定是否返回）
        if include_paid:
            result["is_paid_locked"] = False
            result["tags"] = self.tags
            result["quote"] = self.quote
            result["personality_keyword"] = self.personality_keyword
            result["classic_events"] = self.classic_events
            result["fun_facts"] = self.fun_facts
            result["advice"] = self.advice
            result["related_books"] = self.related_books
        
        return result


# ============================================================
# 相似度计算
# ============================================================

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    计算两个向量的余弦相似度
    
    余弦相似度公式：
    similarity = (A · B) / (||A|| * ||B||)
    
    参数:
        vec1: 第一个向量
        vec2: 第二个向量
    
    返回:
        相似度值（范围 -1 到 1，越接近 1 表示越相似）
    """
    # 检查向量长度
    if len(vec1) != len(vec2):
        raise ValueError(f"向量长度不一致：{len(vec1)} vs {len(vec2)}")
    
    # 计算点积
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    
    # 计算向量模长
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    
    # 防止除零
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    # 计算余弦相似度
    similarity = dot_product / (norm1 * norm2)
    
    return similarity


def calculate_ocean_similarity(
    user_ocean: Dict[str, float],
    character_ocean: Dict[str, float]
) -> float:
    """
    计算用户 OCEAN 向量与人物 OCEAN 向量的相似度
    
    参数:
        user_ocean: 用户的 OCEAN 分数
        character_ocean: 人物的 OCEAN 分数
    
    返回:
        相似度值（范围 0 到 1）
    """
    # 转换为列表
    user_vec = [
        user_ocean.get("O", 0.5),
        user_ocean.get("C", 0.5),
        user_ocean.get("E", 0.5),
        user_ocean.get("A", 0.5),
        user_ocean.get("N", 0.5)
    ]
    
    character_vec = [
        character_ocean.get("O", 0.5),
        character_ocean.get("C", 0.5),
        character_ocean.get("E", 0.5),
        character_ocean.get("A", 0.5),
        character_ocean.get("N", 0.5)
    ]
    
    # 计算余弦相似度
    similarity = cosine_similarity(user_vec, character_vec)
    
    # 将范围从 [-1, 1] 转换为 [0, 1]
    # 因为 OCEAN 分数都是正数，相似度通常在 0.5 以上
    # 这里直接返回原始值，但确保在合理范围内
    return max(0.0, min(1.0, similarity))


# ============================================================
# 热度等级计算
# ============================================================

def calculate_heat_level(
    match_count: int,
    total_characters: int,
    all_match_counts: List[int]
) -> Tuple[str, int]:
    """
    计算人物的热度等级和百分比排名
    
    参数:
        match_count: 该人物的匹配次数
        total_characters: 人物库总人数
        all_match_counts: 所有人物的匹配次数列表
    
    返回:
        (热度等级名称, 百分比排名)
    """
    # 如果人物库为空，返回默认值
    if total_characters == 0 or len(all_match_counts) == 0:
        return ("中等", 50)
    
    # 计算该人物的排名百分比
    # 排名越高（匹配次数越多），百分比越小（越热门）
    sorted_counts = sorted(all_match_counts, reverse=True)
    
    # 找到该人物在排序后的位置
    rank = 0
    for i, count in enumerate(sorted_counts):
        if count <= match_count:
            rank = i
            break
    
    # 计算百分比排名（0-100）
    # rank = 0 表示最热门，percent = 0
    # rank = total-1 表示最冷门，percent = 100
    percent = int((rank / (total_characters - 1)) * 100) if total_characters > 1 else 50
    
    # 根据百分比确定热度等级
    for level_id, level_info in HEAT_LEVELS.items():
        if percent < level_info["range"][1]:
            return (level_info["name"], percent)
    
    # 默认返回最冷门
    return ("最冷门", 100)


# ============================================================
# 匹配逻辑
# ============================================================

def match_character(
    user_ocean: Dict[str, float],
    characters: List[CharacterData],
    top_k: int = 1
) -> List[Tuple[CharacterData, float]]:
    """
    匹配用户与人物库中的人物
    
    参数:
        user_ocean: 用户的 OCEAN 分数
        characters: 人物库列表
        top_k: 返回前 K 个最相似的人物
    
    返回:
        [(人物数据, 相似度), ...] 的列表，按相似度降序排列
    """
    # 过滤可用的人物
    active_characters = [c for c in characters if c.is_active]
    
    # 如果没有可用人物，返回空列表
    if not active_characters:
        return []
    
    # 计算每个人物的相似度
    similarities = []
    for character in active_characters:
        similarity = calculate_ocean_similarity(user_ocean, character.ocean_vector)
        similarities.append((character, similarity))
    
    # 按相似度降序排序
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # 返回前 K 个结果
    return similarities[:top_k]


def get_best_match(
    user_ocean: Dict[str, float],
    characters: List[CharacterData]
) -> Optional[Tuple[CharacterData, float]]:
    """
    获取最佳匹配的人物
    
    如果多个人物相似度相同，随机选择一个。
    
    参数:
        user_ocean: 用户的 OCEAN 分数
        characters: 人物库列表
    
    返回:
        (人物数据, 相似度) 或 None（如果没有可用人物）
    """
    # 获取 Top-K 结果（K=5，检查是否有相同相似度）
    top_matches = match_character(user_ocean, characters, top_k=5)
    
    # 如果没有匹配结果，返回 None
    if not top_matches:
        return None
    
    # 检查是否有相同相似度的人物
    best_similarity = top_matches[0][1]
    same_similarity_chars = [
        (char, sim) for char, sim in top_matches 
        if sim == best_similarity
    ]
    
    # 如果有多个相同相似度的人物，随机选择一个
    if len(same_similarity_chars) > 1:
        return random.choice(same_similarity_chars)
    
    # 返回最佳匹配
    return top_matches[0]


# ============================================================
# 匹配结果封装
# ============================================================

@dataclass
class MatchResult:
    """
    匹配结果类
    
    封装匹配结果的所有信息，包括人物数据、相似度、热度等。
    """
    character: CharacterData                        # 匹配的人物
    similarity: float                               # 相似度（0-1）
    similarity_percent: int                         # 相似度百分比
    heat_level: str                                 # 热度等级名称
    heat_percent: int                               # 热度百分比排名
    is_paid_locked: bool = True                     # 付费字段是否锁定
    
    def to_dict(self, include_paid: bool = False) -> Dict[str, Any]:
        """
        转换为字典格式
        
        参数:
            include_paid: 是否包含付费字段
        
        返回:
            匹配结果的字典
        """
        result = {
            "character": self.character.to_dict(include_paid=include_paid),
            "similarity": self.similarity,
            "similarity_percent": self.similarity_percent,
            "heat_level": self.heat_level,
            "heat_percent": self.heat_percent,
            "is_paid_locked": not include_paid,
        }
        
        return result


def create_match_result(
    character: CharacterData,
    similarity: float,
    total_characters: int,
    all_match_counts: List[int],
    include_paid: bool = False
) -> MatchResult:
    """
    创建匹配结果对象
    
    参数:
        character: 匹配的人物
        similarity: 相似度
        total_characters: 人物库总人数
        all_match_counts: 所有人物的匹配次数列表
        include_paid: 是否包含付费字段
    
    返回:
        MatchResult 对象
    """
    # 计算相似度百分比
    similarity_percent = int(similarity * 100)
    
    # 计算热度等级
    heat_level, heat_percent = calculate_heat_level(
        character.match_count,
        total_characters,
        all_match_counts
    )
    
    # 创建结果对象
    return MatchResult(
        character=character,
        similarity=similarity,
        similarity_percent=similarity_percent,
        heat_level=heat_level,
        heat_percent=heat_percent,
        is_paid_locked=not include_paid
    )


# ============================================================
# 辅助函数
# ============================================================

def validate_source(source: str) -> bool:
    """
    验证来源类型是否有效
    
    参数:
        source: 来源类型
    
    返回:
        是否有效
    """
    return source in SOURCE_TYPES


def validate_era_for_history(source: str, era: str) -> bool:
    """
    验证历史人物的时代是否有效

    历史人物必须是清朝或之前的人物（不含近现代）。
    注：source 参数保留是为了向后兼容调用方式，当前人物库只有历史人物。

    参数:
        source: 来源类型（保留参数，当前始终为"历史"）
        era: 时代

    返回:
        是否有效
    """
    # 历史人物必须有时代
    if not era:
        return False

    # 如果时代包含"现代"、"民国"等近现代关键词，则无效
    invalid_keywords = ["现代", "民国", "近代", "当代", "20世纪", "21世纪"]
    for keyword in invalid_keywords:
        if keyword in era:
            return False

    # 检查是否是清朝或之前的时代（含各朝代常见写法）
    valid_eras = [
        "先秦", "春秋", "战国", "秦朝", "秦代", "汉朝", "汉代", "楚汉",
        "三国", "魏晋", "晋朝", "晋代", "南北朝",
        "隋朝", "隋代", "唐朝", "唐代", "五代",
        "宋朝", "宋代", "元朝", "元代", "明朝", "明代", "清朝", "清代"
    ]
    for valid_era in valid_eras:
        if valid_era in era:
            return True

    # 默认返回 True（允许其他未列举的古代时代写法）
    return True