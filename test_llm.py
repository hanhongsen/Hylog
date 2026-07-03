# ========================================
# LLM 调用模块测试脚本
# ========================================
# 此脚本用于测试 LLM 调用模块是否正常工作
# ========================================

# 导入 LLM 调用模块
from src.utils.llm import chat, count_tokens, get_usage_stats

# ========================================
# 测试 1：Token 计数
# ========================================
print("=" * 50)
print("测试 1：Token 计数")
print("=" * 50)

# 测试文本
test_text = "你好，我是一个测试文本。"

# 计算 token 数量
token_count = count_tokens(test_text)

# 打印结果
print(f"文本: {test_text}")
print(f"Token 数量: {token_count}")
print()

# ========================================
# 测试 2：对话补全
# ========================================
print("=" * 50)
print("测试 2：对话补全")
print("=" * 50)

# 构建消息
messages = [
    {"role": "user", "content": "你好，请用一句话介绍你自己。"}
]

# 调用 AI
print("正在调用 AI...")
try:
    response = chat(messages)
    print(f"AI 回复: {response}")
except Exception as e:
    print(f"调用失败: {e}")

print()

# ========================================
# 测试 3：成本统计
# ========================================
print("=" * 50)
print("测试 3：成本统计")
print("=" * 50)

# 获取使用统计
stats = get_usage_stats()

# 打印结果
print(f"今日消费: {stats['daily_cost']:.6f} 元")
print(f"本月消费: {stats['monthly_cost']:.6f} 元")
print(f"总调用次数: {stats['total_calls']}")
print(f"按功能分类: {stats['function_costs']}")

print()
print("=" * 50)
print("测试完成！")
print("=" * 50)
