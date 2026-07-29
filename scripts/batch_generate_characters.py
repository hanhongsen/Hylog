"""
历史人物库扩充 - 批量AI生成脚本
基于扩展人物名单批量生成完整的1200人物数据

功能：
1. 读取扩展人物名单（character_list_extended.json）
2. 调用AI联网搜索分析每个人物，生成OCEAN向量和详细信息
3. 生成人物图片
4. 存入数据库，支持去重和断点续传

使用方法：
    python scripts/batch_generate_characters.py [--dynasties 夏朝,商朝,周朝] [--batch-size 10] [--continue]

参数：
    --dynasties: 指定要处理的朝代（逗号分隔），默认处理全部
    --batch-size: 每批处理的人物数量，默认10
    --continue: 启用断点续传模式
"""

import os
import sys
import json
import uuid
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入项目模块
from src.utils.llm import analyze_character, generate_character_image, LLMError
from src.data.models import Character, create_tables
from src.matching.matcher import validate_source, validate_era_for_history
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ============================================================
# 配置
# ============================================================

# 扩展人物名单文件路径
CHARACTER_LIST_EXTENDED = project_root / "data" / "characters" / "character_list_extended.json"
# 迷你测试文件路径
CHARACTER_MINI_TEST = project_root / "data" / "characters" / "character_mini_test.json"

# 进度跟踪文件
PROGRESS_FILE = project_root / "data" / "characters" / "generation_progress.json"

# 图片存储目录
IMAGE_DIR = project_root / "data" / "characters" / "images"

# 数据库文件路径
DATABASE_FILE = project_root / "hylog.db"

# 处理间隔（秒，避免API限流）
PROCESS_INTERVAL = 2

# 批次间隔（秒，批次之间的休息时间）
BATCH_INTERVAL = 10

# ============================================================
# 工具类
# ============================================================

class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, progress_file: Path):
        self.progress_file = progress_file
        self.data = self.load_progress()
    
    def load_progress(self) -> Dict[str, Any]:
        """加载进度数据"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {"processed": [], "failed": [], "statistics": {}}
        else:
            return {"processed": [], "failed": [], "statistics": {}}
    
    def save_progress(self):
        """保存进度数据"""
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def mark_processed(self, character_id: str):
        """标记为已处理"""
        if character_id not in self.data["processed"]:
            self.data["processed"].append(character_id)
        self.save_progress()
    
    def mark_failed(self, character_id: str, error: str = ""):
        """标记为失败"""
        self.data["failed"].append({
            "character_id": character_id,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        self.save_progress()
    
    def is_processed(self, character_id: str) -> bool:
        """检查是否已处理"""
        return character_id in self.data["processed"]
    
    def update_statistics(self, stats: Dict[str, Any]):
        """更新统计信息"""
        self.data["statistics"].update(stats)
        self.save_progress()
    
    def get_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        return {
            "total_processed": len(self.data["processed"]),
            "total_failed": len(self.data["failed"]),
            "statistics": self.data["statistics"]
        }


class CharacterGenerator:
    """人物数据生成器"""
    
    def __init__(self, session: sessionmaker, progress_tracker: ProgressTracker):
        self.session = session
        self.progress_tracker = progress_tracker
        self.processed_count = 0
        self.failed_count = 0
        self.skip_count = 0
    
    def process_character(self, character_id: str, character_info: Dict[str, str]) -> bool:
        """处理单个人物"""
        name = character_info.get("name", "")
        source = character_info.get("source", "")
        era = character_info.get("era", "")
        
        # 检查是否是占位符
        is_placeholder = character_info.get("placeholder", False)
        
        if is_placeholder:
            print(f"  [{character_id}] ⏭️ 跳过占位符：{name}（需要手动完善）")
            self.skip_count += 1
            return False
        
        # 检查进度（如果启用断点续传）
        if self.progress_tracker.is_processed(character_id):
            print(f"  [{character_id}] ⏭️ 跳过已处理：{name}")
            self.skip_count += 1
            return False
        
        # 验证基本信息
        if not name or not source:
            print(f"  [{character_id}] ❌ 人物信息不完整")
            self.failed_count += 1
            self.progress_tracker.mark_failed(character_id, "信息不完整")
            return False
        
        # 验证来源类型
        if not validate_source(source):
            print(f"  [{character_id}] ❌ 来源类型无效：{source}")
            self.failed_count += 1
            self.progress_tracker.mark_failed(character_id, f"无效来源：{source}")
            return False
        
        # 验证历史人物时代
        if not validate_era_for_history(source, era):
            print(f"  [{character_id}] ❌ 历史人物时代无效：{era}")
            self.failed_count += 1
            self.progress_tracker.mark_failed(character_id, f"无效时代：{era}")
            return False
        
        # 检查数据库中是否已存在
        if self.check_existing_character(name, source):
            print(f"  [{character_id}] ⏭️ 跳过已存在：{name}")
            self.skip_count += 1
            return True
        
        print(f"  [{character_id}] 📖 开始处理：{name}（{source}，{era}）")
        
        try:
            # 调用AI分析人物
            print(f"  [{character_id}] 🤖 调用AI分析人物...")
            analysis_result = analyze_character(name, source, era)
            
            # 检查解析错误
            if analysis_result.get("parse_error"):
                print(f"  [{character_id}] ⚠️ AI返回格式异常，使用默认值")
            
            # 生成人物图片
            print(f"  [{character_id}] 🎨 生成人物图片...")
            try:
                image_path = generate_character_image(
                    name,
                    analysis_result.get("description", ""),
                    source,
                    str(IMAGE_DIR)
                )
                print(f"  [{character_id}] 🖼️ 图片已保存：{image_path}")
            except LLMError as e:
                print(f"  [{character_id}] ⚠️ 图片生成失败：{e}")
                image_path = ""
            
            # 处理相关书籍字段（如果是列表则转为JSON字符串）
            related_books = analysis_result.get("related_books", "")
            if isinstance(related_books, list):
                import json as json_module
                related_books = json_module.dumps(related_books, ensure_ascii=False)
            elif isinstance(related_books, str) and related_books:
                # 如果已经是字符串，直接使用
                pass
            
            # 创建Character对象
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
                related_books=related_books,
                match_count=0,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 存入数据库
            db_session = self.session()
            try:
                db_session.add(character)
                db_session.commit()
                
                # 显示OCEAN分数
                ocean = character.ocean_vector
                print(f"  [{character_id}] ✅ 处理完成：O={ocean['O']:.2f} C={ocean['C']:.2f} E={ocean['E']:.2f} A={ocean['A']:.2f} N={ocean['N']:.2f}")
            finally:
                db_session.close()
            
            # 标记为已处理
            self.progress_tracker.mark_processed(character_id)
            self.processed_count += 1
            
            return True
            
        except LLMError as e:
            print(f"  [{character_id}] ❌ AI调用失败：{e}")
            self.failed_count += 1
            self.progress_tracker.mark_failed(character_id, f"AI错误：{e}")
            return False
        except Exception as e:
            print(f"  [{character_id}] ❌ 处理失败：{e}")
            self.failed_count += 1
            self.progress_tracker.mark_failed(character_id, f"处理错误：{e}")
            return False
    
    def check_existing_character(self, name: str, source: str) -> bool:
        """检查人物是否已存在于数据库"""
        db_session = self.session()
        existing = db_session.query(Character).filter(
            Character.name == name,
            Character.source == source
        ).first()
        db_session.close()
        return existing is not None
    
    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            "processed": self.processed_count,
            "failed": self.failed_count,
            "skipped": self.skip_count
        }


def filter_characters_by_dynasty(character_list: Dict[str, Dict[str, str]], 
                                 target_dynasties: List[str]) -> Dict[str, Dict[str, str]]:
    """根据朝代筛选人物"""
    filtered = {}
    for char_id, char_info in character_list.items():
        era = char_info.get("era", "")
        if era in target_dynasties:
            filtered[char_id] = char_info
    return filtered


def init_database() -> sessionmaker:
    """初始化数据库连接"""
    engine = create_engine(f"sqlite:///{DATABASE_FILE}")
    create_tables(engine)
    Session = sessionmaker(bind=engine)
    print(f"✅ 数据库初始化完成：{DATABASE_FILE}")
    return Session


def load_extended_character_list() -> Dict[str, Dict[str, str]]:
    """加载扩展人物名单"""
    if not CHARACTER_LIST_EXTENDED.exists():
        print(f"❌ 扩展人物名单不存在：{CHARACTER_LIST_EXTENDED}")
        print(f"请先运行：python scripts/generate_character_list.py")
        return {}
    
    try:
        with open(CHARACTER_LIST_EXTENDED, 'r', encoding='utf-8') as f:
            character_list = json.load(f)
        
        print(f"✅ 成功加载扩展人物名单，共 {len(character_list)} 人")
        return character_list
    except json.JSONDecodeError as e:
        print(f"❌ 人物名单文件格式错误：{e}")
        return {}

def load_json_file(file_path: Path) -> Dict[str, Dict[str, str]]:
    """加载JSON人物名单文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            character_list = json.load(f)
        
        print(f"✅ 成功加载人物名单，共 {len(character_list)} 人")
        return character_list
    except json.JSONDecodeError as e:
        print(f"❌ 人物名单文件格式错误：{e}")
        return {}


def process_batch(character_generator: CharacterGenerator, 
                 batch_characters: Dict[str, Dict[str, str]],
                 batch_num: int) -> Dict[str, int]:
    """处理一批人物"""
    print(f"\n{'='*60}")
    print(f"处理批次 {batch_num}（{len(batch_characters)} 人）")
    print(f"{'='*60}")
    
    for char_id, char_info in batch_characters.items():
        character_generator.process_character(char_id, char_info)
        time.sleep(PROCESS_INTERVAL)
    
    stats = character_generator.get_statistics()
    print(f"\n批次 {batch_num} 完成：成功 {stats['processed']}，失败 {stats['failed']}，跳过 {stats['skipped']}")
    
    return stats


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="批量生成历史人物数据")
    parser.add_argument("--dynasties", type=str, help="指定要处理的朝代（逗号分隔）")
    parser.add_argument("--batch-size", type=int, default=10, help="每批处理的人物数量")
    parser.add_argument("--continue", dest="continue_mode", action="store_true", help="启用断点续传模式")
    parser.add_argument("--input", type=str, help="指定输入文件路径")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("历史人物库扩充 - 批量AI生成")
    print("=" * 60)
    
    # 确保图片目录存在
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    # 加载扩展人物名单
    if args.input:
        input_file = project_root / "data" / "characters" / args.input
        if input_file.exists():
            print(f"使用自定义输入文件：{input_file}")
            character_list = load_json_file(input_file)
        else:
            print(f"❌ 指定的输入文件不存在：{input_file}")
            return
    else:
        character_list = load_extended_character_list()
        if not character_list:
            return
    
    # 初始化数据库
    Session = init_database()
    
    # 初始化进度跟踪器
    progress_tracker = ProgressTracker(PROGRESS_FILE)
    if args.continue_mode:
        print("✅ 断点续传模式已启用")
    
    # 创建人物生成器
    generator = CharacterGenerator(Session, progress_tracker)
    
    # 根据朝代筛选人物
    if args.dynasties:
        target_dynasties = [d.strip() for d in args.dynasties.split(",")]
        character_list = filter_characters_by_dynasty(character_list, target_dynasties)
        print(f"✅ 筛选朝代：{', '.join(target_dynasties)}（{len(character_list)} 人）")
    
    # 分批处理
    batch_size = args.batch_size
    character_ids = list(character_list.keys())
    total_batches = (len(character_ids) + batch_size - 1) // batch_size
    
    print(f"\n开始处理 {len(character_ids)} 个人物，分 {total_batches} 批")
    print(f"批次大小：{batch_size}")
    print(f"处理间隔：{PROCESS_INTERVAL}秒")
    print(f"批次间隔：{BATCH_INTERVAL}秒")
    
    for batch_num in range(1, total_batches + 1):
        start_idx = (batch_num - 1) * batch_size
        end_idx = min(start_idx + batch_size, len(character_ids))
        batch_ids = character_ids[start_idx:end_idx]
        
        batch_characters = {char_id: character_list[char_id] for char_id in batch_ids}
        
        # 处理批次
        process_batch(generator, batch_characters, batch_num)
        
        # 批次间休息（除了最后一批）
        if batch_num < total_batches:
            print(f"批次间休息 {BATCH_INTERVAL} 秒...")
            time.sleep(BATCH_INTERVAL)
    
    # 最终统计
    stats = generator.get_statistics()
    progress_summary = progress_tracker.get_summary()
    
    print(f"\n{'='*60}")
    print("全部处理完成")
    print(f"{'='*60}")
    print(f"本次处理：成功 {stats['processed']}，失败 {stats['failed']}，跳过 {stats['skipped']}")
    print(f"总体进度：已处理 {progress_summary['total_processed']}，失败 {progress_summary['total_failed']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()