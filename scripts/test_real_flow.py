"""
真实模式端到端流程测试脚本

用预设的"人格一致"的回答（内向 + 高开放性 + 高神经质，类似屈原/李清照画像），
跑完整对话流程，观察：
1. OCEAN 向量能否真实演化（而不是卡在 0.5）
2. 能否触发收敛
3. 最终匹配的人物是否合理

用法：
    set ZHIPU_MODEL=glm-4.7-flash
    python scripts/test_real_flow.py
"""
import os
import sys
import time

# 确保能 import 项目根目录的 src（必须在 import src.* 之前）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保用 glm-4-flash（免费模型）
os.environ["ZHIPU_MODEL"] = "glm-4-flash"
os.environ["USE_MOCK_AGENT"] = "false"

import logging
logging.disable(logging.CRITICAL)

# 重置全局 LLM 客户端，确保读到新的 model 配置
import src.utils.llm as _llm
_llm._client = None

from src.agent.state import AgentState, MIN_ROUNDS, MAX_ROUNDS
from src.agent.nodes import (
    start_node,
    select_dimension_node,
    generate_question_node,
    process_answer_node,
    update_personality_node,
    check_convergence_node,
    match_character_node,
    MOCK_CHARACTERS,
)
from src.personality import PersonalityUpdater


def log(msg):
    print(msg, flush=True)


def main():
    state = AgentState(session_id="test-real", user_id="test", use_mock=False)
    updater = PersonalityUpdater()

    # 一组人格一致的回答（画像：内向、高开放性、高神经质、低宜人性 -> 偏向屈原/李清照）
    persona_answers = [
        "我喜欢一个人安静地看书思考，不喜欢社交。",
        "我经常感到焦虑和不安，情绪起伏比较大。",
        "做决定时我总是反复斟酌，很难果断下决心。",
        "我重视精神追求胜过物质利益。",
        "我很清楚自己的优缺点，经常自我反省。",
        "我对人比较谨慎，不会轻易相信别人。",
        "压力大时我容易崩溃，很难自我调节。",
        "我很有想象力，喜欢幻想和创造。",
        "我对亲密关系既渴望又害怕，患得患失。",
        "我做事容易半途而废，缺乏毅力。",
        "我经常对生活感到迷茫和悲观。",
        "聚会让我感到疲惫，我更愿意独处。",
        "别人觉得我敏感多疑，容易受伤。",
        "我喜欢探索抽象的理论和哲学问题。",
        "遇到困难我倾向于逃避而不是面对。",
        "我对艺术和美有很强的感受力。",
        "我很难信任别人，总防着被伤害。",
        "我经常陷入自我怀疑和内耗。",
    ]

    start_node(state)
    generate_question_node(state)
    log("=== 开始真实模式流程测试 ===")
    log(f"预设回答数: {len(persona_answers)}")
    log("")

    answer_idx = 0
    t0 = time.time()
    for _ in range(MAX_ROUNDS + 2):
        if answer_idx >= len(persona_answers):
            log(">>> 预设回答用尽")
            break
        answer = persona_answers[answer_idx]
        answer_idx += 1

        process_answer_node(state, answer)
        result = update_personality_node(state, answer, updater)

        if result["skipped"]:
            log(f"  [跳过] {result['guidance']}")
            continue
        if not result["success"]:
            select_dimension_node(state)
            generate_question_node(state)
            continue

        converged, details = check_convergence_node(state, updater)
        ocean = state.get_ocean_dict()
        log(
            f"轮{state.turn_count:2d} 维度={state.current_dimension:16s} "
            f"delta={result['ocean_delta']} "
            f"OCEAN={ocean} "
            f"不确定O={state.ocean_vector.get_average_uncertainty():.2f} "
            f"dim11={state.dim11_vector.get_average_uncertainty():.2f} "
            f"收敛={converged}"
        )

        if converged:
            log("\n>>> 触发收敛！")
            break
        if state.turn_count >= MAX_ROUNDS:
            log("\n>>> 达到最大轮次，强制结束")
            break

        select_dimension_node(state)
        generate_question_node(state)

    elapsed = time.time() - t0

    # 匹配
    best = match_character_node(state, MOCK_CHARACTERS)
    log("")
    log("=" * 50)
    log(f"耗时: {elapsed:.1f}s, 总轮次: {state.turn_count}")
    if best:
        char, sim = best
        log("=== 匹配结果 ===")
        log(f"人物: {char.name} ({char.era})")
        log(f"相似度: {sim * 100:.1f}%")
        log(f"最终用户 OCEAN: {state.get_ocean_dict()}")
        log(f"人物     OCEAN: {char.ocean_vector}")
        log(f"人物关键词: {char.personality_keyword}")
    else:
        log("匹配失败：人物库为空")


if __name__ == "__main__":
    main()
