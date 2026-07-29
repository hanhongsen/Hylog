"""
历史人物库扩充 - 质量检查工具
对生成的人物数据进行质量检查和统计分析

功能：
1. 数据完整性检查（必需字段、数据格式）
2. OCEAN向量合理性验证
3. 朝代和阶层分布统计
4. 数据一致性检查
5. 生成质量报告

使用方法：
    python scripts/quality_check.py [--report] [--fix] [--sample N]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from collections import Counter, defaultdict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入项目模块
from src.data.models import Character, create_tables
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

# ============================================================
# 配置
# ============================================================

# 数据库文件路径
DATABASE_FILE = project_root / "hylog.db"

# 统计报告输出路径
REPORT_DIR = project_root / "data" / "characters" / "quality_reports"

# 有效朝代列表（来自验证逻辑）
VALID_ERAS = [
    "先秦", "春秋", "战国", "秦朝", "秦代", "汉朝", "汉代", "楚汉",
    "三国", "魏晋", "晋朝", "晋代", "南北朝",
    "隋朝", "隋代", "唐朝", "唐代", "五代",
    "宋朝", "宋代", "元朝", "元代", "明朝", "明代", "清朝", "清代",
    # 扩展朝代
    "夏朝", "商朝", "西周", "东周春秋", "东周战国", "西汉", "东汉",
    "西晋", "东晋", "五代十国", "北宋", "南宋", "辽朝", "金朝", "西夏"
]

# 必需字段
REQUIRED_FIELDS = ["character_id", "name", "source", "era", "description", "ocean_vector"]

# 新增详细字段
DETAILED_FIELDS = ["classic_events", "fun_facts", "advice", "related_books"]

# ============================================================
# 质量检查器类
# ============================================================

class CharacterQualityChecker:
    """人物数据质量检查器"""
    
    def __init__(self, session: sessionmaker):
        self.session = session
        self.issues = []
        self.warnings = []
        self.stats = defaultdict(int)
        self.detailed_stats = defaultdict(lambda: defaultdict(int))
    
    def check_all(self) -> Dict[str, Any]:
        """执行所有质量检查"""
        print("🔍 开始质量检查...")
        
        # 1. 数据完整性检查
        self.check_data_integrity()
        
        # 2. OCEAN向量合理性检查
        self.check_ocean_vectors()
        
        # 3. 朝代和阶层分布检查
        self.check_distribution()
        
        # 4. 数据一致性检查
        self.check_consistency()
        
        # 5. 新增字段完整性检查
        self.check_detailed_fields()
        
        return self.generate_report()
    
    def check_data_integrity(self):
        """检查数据完整性"""
        print("📋 检查数据完整性...")
        
        db_session = self.session()
        characters = db_session.query(Character).all()
        total = len(characters)
        
        for char in characters:
            # 检查必需字段
            for field in REQUIRED_FIELDS:
                value = getattr(char, field, None)
                if value is None or value == "":
                    self.issues.append({
                        "type": "missing_field",
                        "character_id": char.character_id,
                        "field": field,
                        "name": char.name,
                        "message": f"缺少必需字段：{field}"
                    })
                    self.stats["missing_fields"] += 1
            
            # 检查JSON字段格式
            if char.ocean_vector:
                try:
                    ocean = char.ocean_vector if isinstance(char.ocean_vector, dict) else json.loads(char.ocean_vector)
                    required_keys = ["O", "C", "E", "A", "N"]
                    for key in required_keys:
                        if key not in ocean:
                            self.issues.append({
                                "type": "invalid_ocean_format",
                                "character_id": char.character_id,
                                "name": char.name,
                                "message": f"OCEAN向量缺少维度：{key}"
                            })
                            self.stats["invalid_ocean_format"] += 1
                except (json.JSONDecodeError, TypeError):
                    self.issues.append({
                        "type": "invalid_json",
                        "character_id": char.character_id,
                        "name": char.name,
                        "message": "OCEAN向量JSON格式错误"
                    })
                    self.stats["invalid_json"] += 1
            
            # 检查标签格式
            if char.tags:
                try:
                    tags = char.tags if isinstance(char.tags, list) else json.loads(char.tags)
                    if not isinstance(tags, list):
                        self.issues.append({
                            "type": "invalid_tags_format",
                            "character_id": char.character_id,
                            "name": char.name,
                            "message": "标签应该是数组格式"
                        })
                        self.stats["invalid_tags_format"] += 1
                except (json.JSONDecodeError, TypeError):
                    self.issues.append({
                        "type": "invalid_tags_json",
                        "character_id": char.character_id,
                        "name": char.name,
                        "message": "标签JSON格式错误"
                    })
                    self.stats["invalid_tags_json"] += 1
        
        db_session.close()
        self.stats["total_characters"] = total
        print(f"  ✅ 检查完成：{total} 个人物")


    def check_ocean_vectors(self):
        """检查OCEAN向量合理性"""
        print("📊 检查OCEAN向量合理性...")
        
        db_session = self.session()
        characters = db_session.query(Character).all()
        
        for char in characters:
            try:
                ocean = char.ocean_vector if isinstance(char.ocean_vector, dict) else json.loads(char.ocean_vector)
                
                # 检查数值范围
                for key, value in ocean.items():
                    if not isinstance(value, (int, float)) or value < 0.0 or value > 1.0:
                        self.issues.append({
                            "type": "invalid_ocean_range",
                            "character_id": char.character_id,
                            "name": char.name,
                            "dimension": key,
                            "value": value,
                            "message": f"OCEAN维度{key}值{value}超出范围[0.0-1.0]"
                        })
                        self.stats["invalid_ocean_range"] += 1
                
                # 检查向量合理性（不能全都是0.5）
                if all(abs(v - 0.5) < 0.01 for v in ocean.values()):
                    self.warnings.append({
                        "type": "default_ocean_vector",
                        "character_id": char.character_id,
                        "name": char.name,
                        "message": "OCEAN向量可能使用默认值，缺乏个性化特征"
                    })
                    self.stats["default_ocean_vectors"] += 1
            
            except (json.JSONDecodeError, TypeError, AttributeError):
                # 已在数据完整性检查中处理
                pass
        
        db_session.close()
        print(f"  ✅ 检查完成")
    
    def check_distribution(self):
        """检查朝代和阶层分布"""
        print("📈 检查朝代和阶层分布...")
        
        db_session = self.session()
        
        # 按朝代统计
        era_distribution = db_session.query(
            Character.era, func.count(Character.character_id)
        ).group_by(Character.era).all()
        
        print(f"  📊 朝代分布（{len(era_distribution)}个朝代）：")
        for era, count in sorted(era_distribution, key=lambda x: x[1], reverse=True):
            print(f"    {era}: {count}人")
            self.detailed_stats["eras"][era] = count
        
        # 检查无效朝代
        for era, count in era_distribution:
            if era not in VALID_ERAS:
                self.warnings.append({
                    "type": "invalid_era",
                    "era": era,
                    "count": count,
                    "message": f"朝代'{era}'不在有效朝代列表中"
                })
                self.stats["invalid_eras"] += 1
        
        # 按来源统计
        source_distribution = db_session.query(
            Character.source, func.count(Character.character_id)
        ).group_by(Character.source).all()
        
        print(f"  📊 来源分布：")
        for source, count in source_distribution:
            print(f"    {source}: {count}人")
            self.detailed_stats["sources"][source] = count
        
        db_session.close()
        print(f"  ✅ 检查完成")
    
    def check_consistency(self):
        """检查数据一致性"""
        print("🔗 检查数据一致性...")
        
        db_session = self.session()
        
        # 检查重复人物
        duplicates = db_session.query(
            Character.name, Character.source, func.count(Character.character_id)
        ).group_by(Character.name, Character.source).having(
            func.count(Character.character_id) > 1
        ).all()
        
        for name, source, count in duplicates:
            self.issues.append({
                "type": "duplicate_character",
                "name": name,
                "source": source,
                "count": count,
                "message": f"发现重复人物：{name}({source})存在{count}条记录"
            })
            self.stats["duplicate_characters"] += 1
        
        # 检查图片文件是否存在
        characters = db_session.query(Character).filter(Character.image_path != None).all()
        for char in characters:
            if char.image_path and not Path(char.image_path).exists():
                self.warnings.append({
                    "type": "missing_image",
                    "character_id": char.character_id,
                    "name": char.name,
                    "image_path": char.image_path,
                    "message": "图片文件不存在"
                })
                self.stats["missing_images"] += 1
        
        db_session.close()
        print(f"  ✅ 检查完成")
    
    def check_detailed_fields(self):
        """检查新增详细字段完整性"""
        print("📝 检查新增详细字段完整性...")
        
        db_session = self.session()
        characters = db_session.query(Character).all()
        
        for char in characters:
            # 检查每个新增字段
            for field in DETAILED_FIELDS:
                value = getattr(char, field, None)
                if value is None or value == "":
                    self.warnings.append({
                        "type": "missing_detailed_field",
                        "character_id": char.character_id,
                        "name": char.name,
                        "field": field,
                        "message": f"缺少详细字段：{field}"
                    })
                    self.stats[f"missing_{field}"] += 1
        
        # 统计详细字段覆盖率
        for field in DETAILED_FIELDS:
            field_count = db_session.query(func.count(Character.character_id)).filter(
                getattr(Character, field) != None,
                getattr(Character, field) != ""
            ).scalar()
            
            coverage_rate = (field_count / len(characters) * 100) if characters else 0
            print(f"  📊 {field} 覆盖率: {coverage_rate:.1f}% ({field_count}/{len(characters)})")
            self.detailed_stats["field_coverage"][field] = {
                "count": field_count,
                "total": len(characters),
                "coverage_rate": coverage_rate
            }
        
        db_session.close()
        print(f"  ✅ 检查完成")
    
    def generate_report(self) -> Dict[str, Any]:
        """生成质量报告"""
        print("📋 生成质量报告...")
        
        total_issues = len(self.issues)
        total_warnings = len(self.warnings)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_characters": self.stats.get("total_characters", 0),
                "total_issues": total_issues,
                "total_warnings": total_warnings,
                "quality_score": self.calculate_quality_score()
            },
            "issues": self.issues,
            "warnings": self.warnings,
            "statistics": dict(self.stats),
            "detailed_statistics": {k: dict(v) for k, v in self.detailed_stats.items()},
            "recommendations": self.generate_recommendations()
        }
        
        return report


class QualityReportGenerator:
    """质量报告生成器"""
    
    def __init__(self, quality_checker: CharacterQualityChecker):
        self.quality_checker = quality_checker
    
    def calculate_quality_score(self) -> float:
        """计算质量分数（0-100）"""
        if self.quality_checker.stats.get("total_characters", 0) == 0:
            return 0.0
        
        # 基础分：100分
        score = 100.0
        
        # 严重问题扣分
        score -= len(self.quality_checker.issues) * 2
        
        # 警告扣分
        score -= len(self.quality_checker.warnings) * 0.5
        
        # 确保分数在0-100之间
        return max(0.0, min(100.0, score))
    
    def generate_recommendations(self) -> List[str]:
        """生成改进建议"""
    recommendations = []
    
    if self.stats.get("missing_fields", 0) > 0:
        recommendations.append(f"发现{self.stats['missing_fields']}个缺失字段，需要补充基础信息")
    
    if self.stats.get("invalid_ocean_range", 0) > 0:
        recommendations.append(f"发现{self.stats['invalid_ocean_range']}个OCEAN向量数值异常，需要修正")
    
    if self.stats.get("default_ocean_vectors", 0) > 10:
        recommendations.append(f"发现{self.stats['default_ocean_vectors']}个人物使用默认OCEAN向量，需要个性化分析")
    
    if self.stats.get("duplicate_characters", 0) > 0:
        recommendations.append(f"发现{self.stats['duplicate_characters']}组重复人物，需要去重处理")
    
    # 检查详细字段覆盖率
    for field in DETAILED_FIELDS:
        missing_count = self.stats.get(f"missing_{field}", 0)
        if missing_count > 50:
            recommendations.append(f"字段'{field}'缺失{missing_count}条，建议批量生成或手工补充")
    
    if not recommendations:
        recommendations.append("数据质量良好，建议定期进行质量检查")
    
    return recommendations


def save_report(report: Dict[str, Any], filename: str = None) -> Path:
    """保存质量报告"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quality_report_{timestamp}.json"
    
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / filename
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report_path


def print_report_summary(report: Dict[str, Any]):
    """打印报告摘要"""
    print(f"\n{'='*60}")
    print("质量检查报告摘要")
    print(f"{'='*60}")
    
    summary = report["summary"]
    print(f"总人物数：{summary['total_characters']}")
    print(f"严重问题：{summary['total_issues']}")
    print(f"警告信息：{summary['total_warnings']}")
    print(f"质量分数：{summary['quality_score']:.1f}/100")
    
    if report["issues"]:
        print(f"\n❌ 严重问题（前10条）：")
        for issue in report["issues"][:10]:
            print(f"  - {issue.get('name', 'Unknown')}: {issue.get('message', '')}")
    
    if report["warnings"]:
        print(f"\n⚠️ 警告信息（前10条）：")
        for warning in report["warnings"][:10]:
            print(f"  - {warning.get('name', 'Unknown')}: {warning.get('message', '')}")
    
    if report["recommendations"]:
        print(f"\n💡 改进建议：")
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"  {i}. {rec}")
    
    print(f"{'='*60}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="人物数据质量检查")
    parser.add_argument("--report", action="store_true", help="生成详细质量报告")
    parser.add_argument("--sample", type=int, help="抽样检查指定数量的人物")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("历史人物库扩充 - 质量检查工具")
    print("=" * 60)
    
    # 初始化数据库
    engine = create_engine(f"sqlite:///{DATABASE_FILE}")
    create_tables(engine)
    Session = sessionmaker(bind=engine)
    
    # 创建检查器
    checker = CharacterQualityChecker(Session)
    
    # 执行检查
    report = checker.check_all()
    
    # 打印摘要
    print_report_summary(report)
    
    # 保存详细报告
    if args.report:
        report_path = save_report(report)
        print(f"\n✅ 详细报告已保存：{report_path}")
    
    print(f"\n{'='*60}")
    print("质量检查完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()