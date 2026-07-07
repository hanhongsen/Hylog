"""
种子人物数据脚本

用途：
    把 5 个固定 OCEAN 分数的人物写入数据库的 Character 表，让人物库非空，
    这样真实模式下 ConversationAgent 能完成端到端匹配（不依赖智谱分析人物）。

    注意：这是测试用的种子数据，OCEAN 分数是手工填的粗略值。
    后续运行 build_character_db.py（调智谱做真实联网分析）后，真实数据会覆盖这些。

使用方式（在项目根目录）：
    python scripts/seed_characters.py

参数：
    --db-path PATH   指定数据库路径（默认 hylog.db）
    --force          强制覆盖已存在的人物（默认跳过已存在的）
"""

import argparse
import logging
import sys
from pathlib import Path

# 把项目根目录加入 sys.path，让 src 可导入
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data import init_database, Character, Session as SessionModel  # noqa: E402
from src.agent.nodes import MOCK_CHARACTERS  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def seed(db_path: str, force: bool = False):
    """
    把 MOCK_CHARACTERS 写入数据库

    参数:
        db_path: 数据库文件路径
        force: 是否覆盖已存在的人物
    """
    db_url = f"sqlite:///{db_path}"
    engine, SessionLocal = init_database(db_url)
    db = SessionLocal()

    inserted = 0
    skipped = 0
    updated = 0

    try:
        for char in MOCK_CHARACTERS:
            # 用 name 作为去重键（避免 mock- 前缀的 ID 与真实 ID 混淆）
            existing = db.query(Character).filter_by(name=char.name).first()

            if existing and not force:
                logger.info(f"跳过已存在的人物: {char.name}（用 --force 覆盖）")
                skipped += 1
                continue

            # 生成新的 character_id（去掉 mock- 前缀，用 seed- 前缀标识种子数据）
            new_id = char.character_id.replace("mock-", "seed-")

            if existing and force:
                # 更新已存在的记录
                existing.source = char.source
                existing.era = char.era
                existing.description = char.description
                existing.ocean_vector = char.ocean_vector
                existing.tags = char.tags
                existing.quote = char.quote
                existing.personality_keyword = char.personality_keyword
                existing.is_active = True
                logger.info(f"更新人物: {char.name}")
                updated += 1
            else:
                # 新增记录
                record = Character(
                    character_id=new_id,
                    name=char.name,
                    source=char.source,
                    era=char.era,
                    description=char.description,
                    ocean_vector=char.ocean_vector,
                    image_path="",
                    tags=char.tags,
                    quote=char.quote,
                    personality_keyword=char.personality_keyword,
                    classic_events="",
                    fun_facts="",
                    advice="",
                    related_books="",
                    match_count=0,
                    is_active=True,
                )
                db.add(record)
                logger.info(f"插入人物: {char.name}（{char.source}）")
                inserted += 1

        db.commit()
        logger.info(f"完成！新增 {inserted} 个，更新 {updated} 个，跳过 {skipped} 个")

        # 打印当前人物库
        total = db.query(Character).filter(Character.is_active == True).count()
        logger.info(f"当前人物库共 {total} 个可用人物")

    except Exception as e:
        db.rollback()
        logger.error(f"种子数据写入失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="写入种子人物数据到数据库")
    parser.add_argument(
        "--db-path",
        default="hylog.db",
        help="数据库文件路径（默认 hylog.db）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖已存在的人物（默认跳过）",
    )
    args = parser.parse_args()

    logger.info(f"数据库: {args.db_path}")
    seed(args.db_path, force=args.force)


if __name__ == "__main__":
    main()
