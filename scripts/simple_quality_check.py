"""
简化质量检查工具
检查人物数据的基本质量指标
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.models import Character, create_tables
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

# 数据库文件路径
DATABASE_FILE = project_root / "hylog.db"

def main():
    """主函数"""
    print("=" * 60)
    print("历史人物库扩充 - 简化质量检查")
    print("=" * 60)
    
    # 初始化数据库
    engine = create_engine(f"sqlite:///{DATABASE_FILE}")
    create_tables(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 基本统计
    print("\n📊 基本统计：")
    total_characters = session.query(Character).count()
    print(f"  总人物数：{total_characters}")
    
    # 按朝代统计
    era_distribution = session.query(
        Character.era, func.count(Character.character_id)
    ).group_by(Character.era).all()
    
    print(f"\n📈 朝代分布（{len(era_distribution)}个朝代）：")
    for era, count in sorted(era_distribution, key=lambda x: x[1], reverse=True):
        print(f"  {era}: {count}人")
    
    # 按来源统计
    source_distribution = session.query(
        Character.source, func.count(Character.character_id)
    ).group_by(Character.source).all()
    
    print(f"\n📚 来源分布：")
    for source, count in source_distribution:
        print(f"  {source}: {count}人")
    
    # 检查详细字段覆盖率
    print(f"\n📝 详细字段覆盖率：")
    detailed_fields = ["classic_events", "fun_facts", "advice", "related_books"]
    
    for field in detailed_fields:
        field_count = session.query(func.count(Character.character_id)).filter(
            getattr(Character, field) != None,
            getattr(Character, field) != ""
        ).scalar()
        
        coverage_rate = (field_count / total_characters * 100) if total_characters > 0 else 0
        print(f"  {field}: {coverage_rate:.1f}% ({field_count}/{total_characters})")
    
    # 检查OCEAN向量
    print(f"\n🧠 OCEAN向量检查：")
    characters = session.query(Character).all()
    
    default_vectors = 0
    invalid_vectors = 0
    
    for char in characters:
        try:
            ocean = char.ocean_vector if isinstance(char.ocean_vector, dict) else json.loads(char.ocean_vector)
            
            # 检查是否是默认向量
            if all(abs(v - 0.5) < 0.01 for v in ocean.values()):
                default_vectors += 1
            
            # 检查数值范围
            for key, value in ocean.items():
                if not isinstance(value, (int, float)) or value < 0.0 or value > 1.0:
                    invalid_vectors += 1
                    break
                    
        except (json.JSONDecodeError, TypeError):
            invalid_vectors += 1
    
    print(f"  正常向量：{total_characters - default_vectors - invalid_vectors}")
    print(f"  默认向量：{default_vectors}")
    print(f"  异常向量：{invalid_vectors}")
    
    # 质量分数
    print(f"\n📋 数据质量评估：")
    quality_issues = invalid_vectors * 2 + default_vectors
    quality_score = max(0, 100 - quality_issues)
    print(f"  质量分数：{quality_score}/100")
    
    # 推荐下一步
    print(f"\n💡 建议下一步：")
    if total_characters < 50:
        print("  1. 继续完成中规模测试（目标150人）")
        print("  2. 提升详细字段覆盖率")
    elif total_characters < 1200:
        print("  1. 开始大规模批量生成")
        print("  2. 优化OCEAN向量个性化")
    else:
        print("  1. 数据生成已完成")
        print("  2. 进行最终质量审核")
    
    session.close()
    print(f"\n{'='*60}")
    print("质量检查完成")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()