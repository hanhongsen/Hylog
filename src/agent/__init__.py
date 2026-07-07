"""
Agent 调度模块

本模块是 Hylog 系统的"控制中心"，负责协调所有模块的调用与状态流转，
将单轮对话变成一个完整的人格建模闭环。

核心架构：
    用户回答 → Agent → [问题生成器] → [人格更新器] → [收敛判断] → [人物匹配] → 结果
                      ↑                                                              │
                      └──────── 未收敛/验证未通过，继续对话 ←─────────────────────────┘

主要组件：
    AgentState        - 会话状态（记忆），贯穿一次完整对话
    ConversationAgent - 主控制器，编排节点 + 路由决策 + 持久化
    nodes             - 8 个流程节点函数（职责单一，可独立测试）

使用示例：
    from src.agent import ConversationAgent

    # 创建并开始对话（Mock 模式，开发推荐）
    agent = ConversationAgent.create(use_mock=True)
    response = agent.start()
    print(response["question"])  # 开场白 + 第一个问题

    # 多轮对话
    response = agent.reply("我喜欢一个人看书看电影")
    print(response["question"])  # 下一个问题
    print(response["personality_state"])  # 当前人格状态

    # 判断是否结束
    if response["is_finished"]:
        result = response["result"]
        print(f"你的匹配人物：{result['character']['name']}")

便捷函数：
    run_conversation_demo() - 运行一个 Mock 模式的完整对话演示
"""

from .state import (
    AgentState,
    OPENING_MESSAGE,
    MIN_ROUNDS,
    MIN_EXPLORE_PER_DIMENSION,
    MAX_UNCERTAINTY,
    MAX_ROUNDS,
    OCEAN_SIMILARITY_REFERENCE,
)

from .nodes import (
    start_node,
    select_dimension_node,
    generate_question_node,
    process_answer_node,
    update_personality_node,
    check_convergence_node,
    match_character_node,
    build_result_node,
    MOCK_CHARACTERS,
)

from .graph import ConversationAgent


# ============================================================
# 模块导出列表
# ============================================================

__all__ = [
    # 主类
    "ConversationAgent",

    # 状态
    "AgentState",
    "OPENING_MESSAGE",
    "MIN_ROUNDS",
    "MIN_EXPLORE_PER_DIMENSION",
    "MAX_UNCERTAINTY",
    "MAX_ROUNDS",
    "OCEAN_SIMILARITY_REFERENCE",

    # 节点函数
    "start_node",
    "select_dimension_node",
    "generate_question_node",
    "process_answer_node",
    "update_personality_node",
    "check_convergence_node",
    "match_character_node",
    "build_result_node",

    # Mock 数据
    "MOCK_CHARACTERS",
]
