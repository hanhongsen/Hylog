"""
人物库预处理脚本

本脚本用于批量构建人物库数据：
1. 读取人物名单文件（character_list.json）
2. 调用 AI（联网搜索）分析每个人物
3. 调用 AI 生成人物图片
4. 将所有数据存入数据库

使用方法：
    python scripts/build_character_db.py

注意：
- 运行前请确保 .env 文件中配置了智谱 API Key
- 人物名单文件位于 data/characters/character_list.json
- 图片存储在 data/characters/images/ 目录
"""

import os
import sys
import json
import uuid
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入项目模块
from src.utils.llm import analyze_character, generate_character_image, LLMError
from src.data.models import Character, create_tables, Base
from src.matching.matcher import validate_source, validate_era_for_history
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ============================================================
# 配置
# ============================================================

# 人物名单文件路径
CHARACTER_LIST_FILE = project_root / "data" / "characters" / "character_list.json"

# 图片存储目录
IMAGE_DIR = project_root / "data" / "characters" / "images"

# 数据库文件路径
DATABASE_FILE = project_root / "data" / "hylog.db"

# 处理间隔（秒，避免 API 限流）
PROCESS_INTERVAL = 2


# ============================================================
# 辅助函数
# ============================================================

def load_character_list() -> Dict[str, Dict[str, str]]:
    """
    加载人物名单文件
    
    返回:
        人物名单字典，格式为：
        {
            "1": {"name": "诸葛亮", "source": "历史", "era": "三国时期"},
            "2": {"name": "林黛玉", "source": "文学", "era": ""},
            ...
        }
    """
    # 检查文件是否存在
    if not CHARACTER_LIST_FILE.exists():
        print(f"❌ 人物名单文件不存在：{CHARACTER_LIST_FILE}")
        print(f"请先创建人物名单文件，格式如下：")
        print(json.dumps({
            "1": {"name": "诸葛亮", "source": "历史", "era": "三国时期"},
            "2": {"name": "林黛玉", "source": "文学", "era": ""}
        }, ensure_ascii=False, indent=2))
        return {}
    
    # 读取文件
    try:
        with open(CHARACTER_LIST_FILE, "r", encoding="utf-8") as f:
            character_list = json.load(f)
        
        print(f"✅ 成功加载人物名单，共 {len(character_list)} 人")
        return character_list
        
    except json.JSONDecodeError as e:
        print(f"❌ 人物名单文件格式错误：{e}")
        return {}


def ensure_image_dir() -> None:
    """
    确保图片存储目录存在
    """
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✅ 图片存储目录：{IMAGE_DIR}")


def init_database() -> sessionmaker:
    """
    初始化数据库连接
    
    返回:
        SQLAlchemy Session 工厂
    """
    # 创建数据库引擎
    engine = create_engine(f"sqlite:///{DATABASE_FILE}")
    
    # 创建表（如果不存在）
    create_tables(engine)
    
    # 创建 Session 工厂
    Session = sessionmaker(bind=engine)
    
    print(f"✅ 数据库初始化完成：{DATABASE_FILE}")
    return Session


def process_character(
    character_info: Dict[str, str],
    session: sessionmaker,
    index: str
) -> Optional[Character]:
    """
    处理单个人物
    
    参数:
        character_info: 人物信息（name, source, era）
        session: 数据库 Session
        index: 人物索引
    
    返回:
        Character 对象，如果处理失败则返回 None
    """
    name = character_info.get("name", "")
    source = character_info.get("source", "")
    era = character_info.get("era", "")
    
    # 验证基本信息
    if not name or not source:
        print(f"  [{index}] ❌ 人物信息不完整：{character_info}")
        return None
    
    # 验证来源类型
    if not validate_source(source):
        print(f"  [{index}] ❌ 来源类型无效：{source}（有效值：历史、文学、影视）")
        return None
    
    # 验证历史人物时代
    if not validate_era_for_history(source, era):
        print(f"  [{index}] ❌ 历史人物时代无效：{era}（必须是清朝或之前）")
        return None
    
    print(f"  [{index}] 开始处理：{name}（{source}）")
    
    try:
        # 调用 AI 分析人物
        print(f"  [{index}] 📖 调用 AI 分析人物...")
        analysis_result = analyze_character(name, source, era)
        
        # 检查是否有解析错误
        if analysis_result.get("parse_error"):
            print(f"  [{index}] ⚠️ AI 返回格式异常，使用默认值")
        
        # 生成人物图片
        print(f"  [{index}] 🎨 生成人物图片...")
        try:
            image_path = generate_character_image(
                name, 
                analysis_result.get("description", ""), 
                source,
                str(IMAGE_DIR)
            )
            print(f"  [{index}] 🖼️ 图片已保存：{image_path}")
        except LLMError as e:
            print(f"  [{index}] ⚠️ 图片生成失败：{e}")
            image_path = ""
        
        # 创建 Character 对象
        character = Character(
            character_id=str(uuid.uuid4()),
            name=name,
            source=source,
            era=era,
            description=analysis_result.get("description", ""),
            ocean_vector={
                "O": analysis_result.get("O", 0.5),
                "C": analysis_result.get("C", 0.5),
                "E": analysis_result.get("E", 0.5),
                "A": analysis_result.get("A", 0.5),
                "N": analysis_result.get("N", 0.5)
            },
            image_path=image_path,
            tags=analysis_result.get("tags", []),
            quote=analysis_result.get("quote", ""),
            personality_keyword=analysis_result.get("personality_keyword", ""),
            classic_events=analysis_result.get("classic_events", ""),
            fun_facts=analysis_result.get("fun_facts", ""),
            advice=analysis_result.get("advice", ""),
            related_books=analysis_result.get("related_books", ""),
            match_count=0,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 存入数据库
        db_session = session()
        db_session.add(character)
        db_session.commit()
        db_session.close()
        
        print(f"  [{index}] ✅ 处理完成：{name}")
        
        # 显示 OCEAN 分数
        ocean = character.ocean_vector
        print(f"       O={ocean['O']:.2f} C={ocean['C']:.2f} E={ocean['E']:.2f} A={ocean['A']:.2f} N={ocean['N']:.2f}")
        
        return character
        
    except LLMError as e:
        print(f"  [{index}] ❌ AI 调用失败：{e}")
        return None
    
    except Exception as e:
        print(f"  [{index}] ❌ 处理失败：{e}")
        return None


def check_existing_character(name: str, source: str, session: sessionmaker) -> bool:
    """
    检查人物是否已存在于数据库
    
    参数:
        name: 人物名称
        source: 来源
        session: 数据库 Session
    
    返回:
        是否存在
    """
    db_session = session()
    existing = db_session.query(Character).filter(
        Character.name == name,
        Character.source == source
    ).first()
    db_session.close()
    
    return existing is not None


def skip_existing_character(name: str, source: str, index: str) -> None:
    """
    跳过已存在的人物
    
    参数:
        name: 人物名称
        source: 来源
        index: 人物索引
    """
    print(f"  [{index}] ⏭️ 跳过已存在：{name}（{source}）")


# ============================================================
# 主函数
# ============================================================

def main():
    """
    主函数：批量处理人物名单
    """
    print("=" * 60)
    print("人物库预处理脚本")
    print("=" * 60)
    
    # 加载人物名单
    character_list = load_character_list()
    if not character_list:
        return
    
    # 确保图片目录存在
    ensure_image_dir()
    
    # 初始化数据库
    Session = init_database()
    
    # 统计处理结果
    total = len(character_list)
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    print("\n" + "=" * 60)
    print(f"开始处理 {total} 个人物")
    print("=" * 60 + "\n")
    
    # 遍历人物名单
    for index, character_info in character_list.items():
        name = character_info.get("name", "")
        source = character_info.get("source", "")
        
        # 检查是否已存在
        if check_existing_character(name, source, Session):
            skip_existing_character(name, source, index)
            skip_count += 1
            continue
        
        # 处理人物
        result = process_character(character_info, Session, index)
        
        if result:
            success_count += 1
        else:
            fail_count += 1
        
        # 处理间隔（避免 API 限流）
        time.sleep(PROCESS_INTERVAL)
    
    # 显示统计结果
    print("\n" + "=" * 60)
    print("处理完成")
    print("=" * 60)
    print(f"总计：{total} 人")
    print(f"成功：{success_count} 人")
    print(f"跳过：{skip_count} 人")
    print(f"失败：{fail_count} 人")
    print("=" * 60)


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    main()