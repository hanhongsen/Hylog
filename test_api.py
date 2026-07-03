"""
API 调用测试脚本

用于验证智谱 AI 的 API 调用是否正常工作。
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

# 设置环境变量（确保使用正确的 API Key）
os.environ["ZHIPU_API_KEY"] = os.getenv("ZHIPU_API_KEY", "")
os.environ["ZHIPU_MODEL"] = os.getenv("ZHIPU_MODEL", "glm-4")

# 导入模块
from src.utils.llm import get_client, analyze_character, generate_character_image, LLMError


def test_analyze_character():
    """
    测试人物分析功能（联网搜索）
    """
    print("\n" + "=" * 60)
    print("测试人物分析功能（联网搜索）")
    print("=" * 60)
    
    try:
        # 测试分析一个人物
        result = analyze_character("诸葛亮", "历史", "三国时期")
        
        print(f"\n✅ 分析成功！")
        print(f"人物名称：诸葛亮")
        print(f"OCEAN 分数：")
        print(f"  O(开放性): {result.get('O', 0):.2f}")
        print(f"  C(责任心): {result.get('C', 0):.2f}")
        print(f"  E(外向性): {result.get('E', 0):.2f}")
        print(f"  A(宜人性): {result.get('A', 0):.2f}")
        print(f"  N(神经质): {result.get('N', 0):.2f}")
        
        if "description" in result:
            print(f"\n简介：{result['description'][:100]}...")
        if "tags" in result:
            print(f"标签：{result['tags']}")
        if "quote" in result:
            print(f"语录：{result['quote'][:50]}")
        
        return True
        
    except LLMError as e:
        print(f"\n❌ 人物分析失败：{e}")
        return False
        
    except Exception as e:
        print(f"\n❌ 未知错误：{e}")
        return False


def test_generate_image():
    """
    测试图片生成功能
    """
    print("\n" + "=" * 60)
    print("测试图片生成功能")
    print("=" * 60)
    
    try:
        # 测试生成一张图片
        image_path = generate_character_image(
            "诸葛亮",
            "三国时期蜀汉丞相，足智多谋，善于谋划，性格谨慎稳重",
            "历史",
            "data/characters/images"
        )
        
        print(f"\n✅ 图片生成成功！")
        print(f"图片路径：{image_path}")
        
        # 检查文件是否存在
        if os.path.exists(image_path):
            file_size = os.path.getsize(image_path)
            print(f"文件大小：{file_size} bytes")
        else:
            print(f"⚠️ 图片文件不存在：{image_path}")
        
        return True
        
    except LLMError as e:
        print(f"\n❌ 图片生成失败：{e}")
        return False
        
    except Exception as e:
        print(f"\n❌ 未知错误：{e}")
        return False


def test_basic_chat():
    """
    测试基础对话功能
    """
    print("\n" + "=" * 60)
    print("测试基础对话功能")
    print("=" * 60)
    
    try:
        client = get_client()
        
        # 测试简单对话
        response = client.chat(
            messages=[{"role": "user", "content": "你好"}]
        )
        
        print(f"\n✅ 对话成功！")
        print(f"AI 回复：{response[:50]}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 对话失败：{e}")
        return False


def main():
    """
    主函数：运行所有测试
    """
    print("=" * 60)
    print("Hylog API 调用测试")
    print("=" * 60)
    
    # 检查 API Key
    if not os.getenv("ZHIPU_API_KEY"):
        print("\n❌ 请先配置 ZHIPU_API_KEY 环境变量")
        print("请在 .env 文件中添加：ZHIPU_API_KEY=your_api_key")
        return
    
    # 运行测试
    results = []
    
    # 测试基础对话
    results.append(("基础对话", test_basic_chat()))
    
    # 测试人物分析（联网搜索）
    results.append(("人物分析", test_analyze_character()))
    
    # 测试图片生成
    results.append(("图片生成", test_generate_image()))
    
    # 显示结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！可以继续开发后续模块。")
    else:
        print("\n⚠️ 部分测试失败，请检查 API 配置。")


if __name__ == "__main__":
    main()