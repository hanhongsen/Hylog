"""
手动添加测试人物数据

由于API余额不足，跳过图片生成，直接添加人物信息到数据库
"""

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.models import Character, create_tables

# 数据库文件路径
DATABASE_FILE = project_root / "hylog.db"

# 测试人物数据（模拟AI分析结果）
test_characters = [
    {
        "name": "西施",
        "source": "历史",
        "era": "春秋",
        "description": "西施，春秋时期越国美女，相传为越王勾践献给吴王夫差，以助越国灭吴。她以美貌著称，被后人尊为四大美女之一。",
        "ocean_vector": {"O": 0.45, "C": 0.38, "E": 0.5, "A": 0.65, "N": 0.25},
        "tags": ["美女", "政治工具", "文化符号", "忠诚", "牺牲"],
        "quote": "沉鱼落雁，闭月羞花。",
        "personality_keyword": "美丽智慧型",
        "classic_events": "1. 西施被迫远赴吴国，成为吴王夫差的爱妃，暗中传递越国情报。2. 西施的美貌成为吴王夫差沉迷享乐的原因之一，间接导致吴国衰败。3. 越国灭吴后，西施的生死成谜，但她的故事流传千古。",
        "fun_facts": "西施的真实存在性在史学界存在争议，但她的故事在中国文化中具有极高的知名度。",
        "advice": "在面对逆境时，保持智慧和美丽，用内在的力量去影响他人。",
        "related_books": [
            {"title": "《越绝书》", "description": "记录了西施及其相关历史事件的古籍，是了解西施生平的重要资料。"},
            {"title": "《东周列国志》", "description": "小说形式的历史著作，其中包含了对西施故事的描述。"},
            {"title": "《中国古代四大美女》", "description": "介绍中国古代四大美女的书籍，其中对西施有详细的分析和评价。"}
        ]
    },
    {
        "name": "鲁班",
        "source": "历史", 
        "era": "春秋",
        "description": "鲁班，春秋时期著名工匠，被誉为百工之祖。他擅长制作各种器械和建筑，对后世影响深远。",
        "ocean_vector": {"O": 0.85, "C": 0.75, "E": 0.6, "A": 0.5, "N": 0.3},
        "tags": ["发明家", "工匠", "建筑大师", "智慧型", "创新型"],
        "quote": "工欲善其事，必先利其器。",
        "personality_keyword": "智慧创新型",
        "classic_events": "鲁班发明了锯、刨子等工具，提高了木工效率；参与建造了著名的赵州桥。",
        "fun_facts": "鲁班不仅擅长木工，还涉猎机械制造，据说他发明了木鸢，能够飞行。",
        "advice": "培养创新思维，勇于尝试新事物，同时注重实践和技能的提升。",
        "related_books": [
            {"title": "《鲁班传》", "description": "详细介绍了鲁班的一生及其在工艺技术上的成就。"},
            {"title": "《中国古代科技史》", "description": "书中包含了鲁班的相关内容，以及中国古代科技发展的历史。"},
            {"title": "《百工技艺》", "description": "介绍了古代各种工艺技术，包括鲁班的木工技艺。"}
        ]
    },
    {
        "name": "扁鹊",
        "source": "历史",
        "era": "春秋",
        "description": "扁鹊，春秋时期著名医学家，被誉为中医之祖。他精通各种医术，创立了望、闻、问、切四诊法，对后世医学影响深远。",
        "ocean_vector": {"O": 0.75, "C": 0.88, "E": 0.5, "A": 0.82, "N": 0.35},
        "tags": ["医学家", "中医之祖", "诊断专家", "智慧型", "仁爱型"],
        "quote": "治病必求于本。",
        "personality_keyword": "仁爱智慧型",
        "classic_events": "扁鹊创立了望、闻、问、切四诊法，奠定了中医诊断基础；救治了许多疑难病症患者。",
        "fun_facts": "扁鹊其实不是他的真名，而是因为他医术高超，人们用传说中的神医'扁鹊'来称呼他。",
        "advice": "追求专业卓越的同时，保持对他人的关怀和仁爱之心。",
        "related_books": [
            {"title": "《史记·扁鹊仓公列传》", "description": "司马迁所著，记录了扁鹊的生平和医学成就，是研究古代医学的重要文献。"},
            {"title": "《黄帝内经》", "description": "中医经典著作，虽然不是扁鹊所著，但与他的医学思想一脉相承。"},
            {"title": "《中医诊断学》", "description": "现代中医诊断学教材，详细介绍了扁鹊创立的四诊法及其现代应用。"}
        ]
    }
]

def main():
    """主函数"""
    print("=" * 60)
    print("手动添加测试人物数据")
    print("=" * 60)
    
    # 初始化数据库
    engine = create_engine(f"sqlite:///{DATABASE_FILE}")
    create_tables(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print(f"✅ 数据库初始化完成：{DATABASE_FILE}")
    
    # 统计结果
    added_count = 0
    skipped_count = 0
    
    for char_data in test_characters:
        name = char_data["name"]
        source = char_data["source"]
        
        # 检查是否已存在
        existing = session.query(Character).filter(
            Character.name == name,
            Character.source == source
        ).first()
        
        if existing:
            print(f"⏭️ 跳过已存在：{name}")
            skipped_count += 1
            continue
        
        print(f"📖 添加人物：{name}（{source}，{char_data['era']}）")
        
        # 将相关书籍列表转为JSON字符串
        related_books_str = json.dumps(char_data["related_books"], ensure_ascii=False)
        
        # 创建Character对象
        character = Character(
            character_id=str(uuid.uuid4()),
            name=name,
            source=source,
            era=char_data["era"],
            description=char_data["description"],
            ocean_vector=char_data["ocean_vector"],
            image_path="",  # 暂时为空
            tags=char_data["tags"],
            quote=char_data["quote"],
            personality_keyword=char_data["personality_keyword"],
            classic_events=char_data["classic_events"],
            fun_facts=char_data["fun_facts"],
            advice=char_data["advice"],
            related_books=related_books_str,
            match_count=0,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 存入数据库
        session.add(character)
        session.commit()
        
        # 显示OCEAN分数
        ocean = character.ocean_vector
        print(f"✅ 添加成功：O={ocean['O']:.2f} C={ocean['C']:.2f} E={ocean['E']:.2f} A={ocean['A']:.2f} N={ocean['N']:.2f}")
        
        added_count += 1
    
    # 关闭会话
    session.close()
    
    # 显示统计结果
    print(f"\n{'=' * 60}")
    print("处理完成")
    print(f"{'=' * 60}")
    print(f"成功添加：{added_count} 人")
    print(f"跳过已存在：{skipped_count} 人")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()