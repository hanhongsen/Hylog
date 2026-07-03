"""
OCEAN 五维人格模型定义

本文件定义了 OCEAN(大五人格)模型的详细信息，包括：
- 五个维度的名称、缩写、含义
- 每个维度的 6 个子维度
- 高分和低分的典型特征
- 维度之间的相关性

这些信息主要用于：
1. 帮助开发者理解每个维度的含义
2. 辅助 AI 生成更精准的问题
3. 帮助解释匹配结果
"""

# ============================================================
# 常量定义
# ============================================================

# OCEAN 五个维度的缩写
OCEAN_DIMENSIONS = ["O", "C", "E", "A", "N"]

# OCEAN 五个维度的全称
OCEAN_FULL_NAMES = {
    "O": "Openness",              # 开放性
    "C": "Conscientiousness",     # 责任心
    "E": "Extraversion",          # 外向性
    "A": "Agreeableness",         # 宜人性
    "N": "Neuroticism"            # 神经质
}

# OCEAN 五个维度的中文名称
OCEAN_CHINESE_NAMES = {
    "O": "开放性",
    "C": "责任心",
    "E": "外向性",
    "A": "宜人性",
    "N": "神经质"
}

# OCEAN 五个维度的简要描述
OCEAN_DESCRIPTIONS = {
    "O": "描述个体心智和经验生活的深度、广度和复杂性，包括求知欲、创造力、接受新事物的程度",
    "C": "描述个体的冲动控制能力、组织能力和追求长期目标的坚持性",
    "E": "描述个体对社交环境中奖励信号的敏感性和外向能量行为",
    "A": "描述个体在人际互动中的合作倾向、同理心和利他行为",
    "N": "描述个体体验负面情绪的倾向和情绪调节能力"
}

# ============================================================
# 子维度定义（每个维度包含 6 个子维度）
# ============================================================

# 开放性（O）的 6 个子维度
OPENNESS_FACETS = [
    "Fantasy",        # 幻想 - 活跃的想象力
    "Aesthetics",     # 审美 - 对艺术和美的欣赏
    "Feelings",       # 情感 - 对内在情绪状态的感知
    "Actions",        # 行动 - 对多样性的偏好
    "Ideas",          # 想法 - 智力好奇心
    "Values"          # 价值观 - 挑战传统价值观的意愿
]

# 责任心（C）的 6 个子维度
CONSCIENTIOUSNESS_FACETS = [
    "Competence",        # 能力 - 感觉自己有能力
    "Order",             # 条理 - 组织能力
    "Dutifulness",       # 责任感 - 道德义务感
    "Achievement",       # 追求成就 - 努力工作的动力
    "Self-Discipline",   # 自律 - 克制冲动的能力
    "Deliberation"       # 谨慎 - 行动前的深思熟虑
]

# 外向性（E）的 6 个子维度
EXTRAVERSION_FACETS = [
    "Warmth",           # 热情 - 友好和亲密关系
    "Gregariousness",   # 合群 - 喜欢人群和社交
    "Assertiveness",    # 自信 - 支配和领导倾向
    "Activity",         # 活跃 - 精力水平
    "Excitement",       # 寻求刺激 - 对兴奋的渴望
    "Positive Emotions" # 积极情绪 - 快乐和乐观
]

# 宜人性（A）的 6 个子维度
AGREEABLENESS_FACETS = [
    "Trust",        # 信任 - 相信他人意图
    "Straightforwardness",  # 坦诚 - 直接和诚实
    "Altruism",     # 利他 - 帮助他人的意愿
    "Compliance",   # 顺从 - 避免冲突
    "Modesty",      # 谦虚 - 不自夸
    "Tender-Mindedness"  # 同理心 - 理解他人感受
]

# 神经质（N）的 6 个子维度
NEUROTICISM_FACETS = [
    "Anxiety",       # 焦虑 - 恐惧和担忧倾向
    "Anger",         # 愤怒 - 愤怒和沮丧倾向
    "Depression",    # 抑郁 - 内疚、悲伤倾向
    "Self-Consciousness",  # 自我意识 - 社交场合的羞耻感
    "Impulsiveness", # 冲动 - 难以控制欲望
    "Vulnerability"  # 脆弱 - 应对压力的困难
]

# 所有子维度的汇总字典
OCEAN_FACETS = {
    "O": OPENNESS_FACETS,
    "C": CONSCIENTIOUSNESS_FACETS,
    "E": EXTRAVERSION_FACETS,
    "A": AGREEABLENESS_FACETS,
    "N": NEUROTICISM_FACETS
}

# ============================================================
# 高分和低分特征定义
# ============================================================

# 高分特征：每个维度得分高时的典型表现
HIGH_SCORE_TRAITS = {
    "O": [
        "强烈的求知欲和智力好奇心",
        "对艺术、美和情感体验的高度欣赏",
        "愿意接受新想法和非传统价值观",
        "丰富的想象力，喜欢抽象思维",
        "寻求生活中的多样性"
    ],
    "C": [
        "高度的自律和自控能力",
        "有条理、计划性强",
        "可靠、负责任",
        "追求成就，目标导向",
        "深思熟虑后再行动"
    ],
    "E": [
        "热情、善于社交",
        "自信、果断",
        "活跃、精力充沛",
        "寻求刺激和兴奋",
        "体验积极情绪的频率高"
    ],
    "A": [
        "信任他人",
        "坦诚、直率",
        "利他、乐于助人",
        "顺从、避免冲突",
        "谦虚、有同理心"
    ],
    "N": [
        "容易焦虑、担忧",
        "情绪波动大",
        "容易愤怒、沮丧",
        "在社交场合感到不自在",
        "脆弱、难以应对压力"
    ]
}

# 低分特征：每个维度得分低时的典型表现
LOW_SCORE_TRAITS = {
    "O": [
        "务实、传统、保守",
        "偏好熟悉的事物和常规",
        "对抽象概念兴趣较低",
        "更喜欢具体、实际的事物"
    ],
    "C": [
        "冲动、随性",
        "缺乏计划和组织",
        "拖延、不可靠",
        "容易分心"
    ],
    "E": [
        "内向、安静",
        "偏好独处",
        "精力来源于内部而非外部",
        "社交活动消耗能量"
    ],
    "A": [
        "怀疑、敌对",
        "自私、竞争性强",
        "操纵性、傲慢",
        "容易与人发生冲突"
    ],
    "N": [
        "情绪稳定、冷静",
        "应对压力能力强",
        "恢复力强",
        "不容易受负面情绪影响"
    ]
}

# ============================================================
# 维度之间的相关性
# ============================================================

# 维度相关性矩阵（简化版，仅标注主要相关关系）
# 正相关：两个维度倾向于同时升高或降低
# 负相关：一个维度升高时另一个倾向于降低
DIMENSION_CORRELATIONS = {
    ("O", "E"): "positive_weak",      # 开放性和外向性弱正相关
    ("O", "N"): "none",               # 开放性和神经质无明显相关
    ("C", "N"): "negative_weak",      # 责任心和神经质弱负相关
    ("E", "N"): "negative_weak",      # 外向性和神经质弱负相关
    ("A", "N"): "negative_weak"       # 宜人性和神经质弱负相关
}

# ============================================================
# 辅助函数
# ============================================================

def get_dimension_info(dimension: str) -> dict:
    """
    获取指定维度的完整信息
    
    参数:
        dimension: 维度缩写(O/C/E/A/N)
    
    返回:
        包含维度所有信息的字典
    """
    # 验证维度是否有效
    if dimension not in OCEAN_DIMENSIONS:
        raise ValueError(f"无效的维度: {dimension}，有效值为: {OCEAN_DIMENSIONS}")
    
    # 构建并返回维度信息字典
    return {
        "abbreviation": dimension,                                    # 缩写
        "full_name": OCEAN_FULL_NAMES[dimension],                    # 全称
        "chinese_name": OCEAN_CHINESE_NAMES[dimension],              # 中文名称
        "description": OCEAN_DESCRIPTIONS[dimension],                # 描述
        "facets": OCEAN_FACETS[dimension],                           # 子维度列表
        "high_score_traits": HIGH_SCORE_TRAITS[dimension],           # 高分特征
        "low_score_traits": LOW_SCORE_TRAITS[dimension]              # 低分特征
    }


def validate_score(score: float) -> bool:
    """
    验证分数是否在有效范围内
    
    参数:
        score: 分数值
    
    返回:
        True 表示有效，False 表示无效
    """
    # 分数必须在 0.0 到 1.0 之间
    return 0.0 <= score <= 1.0


def get_score_level(score: float) -> str:
    """
    根据分数获取等级描述
    
    参数:
        score: 分数值（0.0 ~ 1.0）
    
    返回:
        等级描述字符串
    """
    # 验证分数有效性
    if not validate_score(score):
        raise ValueError(f"无效的分数: {score}，分数必须在 0.0 到 1.0 之间")
    
    # 根据分数范围返回对应等级
    if score >= 0.8:
        return "很高"        # 0.8 ~ 1.0
    elif score >= 0.6:
        return "较高"        # 0.6 ~ 0.8
    elif score >= 0.4:
        return "中等"        # 0.4 ~ 0.6
    elif score >= 0.2:
        return "较低"        # 0.2 ~ 0.4
    else:
        return "很低"        # 0.0 ~ 0.2


def get_all_dimensions_info() -> dict:
    """
    获取所有维度的完整信息
    
    返回:
        包含所有维度信息的字典，以维度缩写为键
    """
    # 遍历所有维度，收集信息
    all_info = {}
    for dimension in OCEAN_DIMENSIONS:
        all_info[dimension] = get_dimension_info(dimension)
    
    return all_info
