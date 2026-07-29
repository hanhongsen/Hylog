#!/usr/bin/env python3
"""
历史人物库扩充 - 人物名单生成脚本
为24个朝代生成完整的1200个人物名单
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
import uuid

# 24个朝代分类体系
DYNASTIES = {
    # 上古时期（3朝代）
    "夏朝": "上古时期",
    "商朝": "上古时期", 
    "西周": "上古时期",
    
    # 春秋战国（2朝代）
    "东周春秋": "春秋战国",
    "东周战国": "春秋战国",
    
    # 秦汉时期（4朝代）
    "秦朝": "秦汉时期",
    "楚汉": "秦汉时期",
    "西汉": "秦汉时期",
    "东汉": "秦汉时期",
    
    # 魏晋南北朝（4朝代）
    "三国": "魏晋南北朝",
    "西晋": "魏晋南北朝", 
    "东晋": "魏晋南北朝",
    "南北朝": "魏晋南北朝",
    
    # 隋唐五代（3朝代）
    "隋朝": "隋唐五代",
    "唐朝": "隋唐五代",
    "五代十国": "隋唐五代",
    
    # 宋辽金西夏（5朝代）
    "北宋": "宋辽金西夏",
    "南宋": "宋辽金西夏",
    "辽朝": "宋辽金西夏",
    "金朝": "宋辽金西夏",
    "西夏": "宋辽金西夏",
    
    # 元明清（3朝代）
    "元朝": "元明清",
    "明朝": "元明清",
    "清朝": "元明清"
}

# 阶层分布配置
SOCIAL_CLASSES = {
    "政治": 15,    # 30% - 皇帝、后妃、王侯、大臣、将领
    "文化": 15,    # 30% - 思想家、文学家、艺术家、学者
    "社会": 12,    # 24% - 商人、工匠、医者、宗教人士、侠客
    "科技": 5,     # 10% - 科学家、发明家、技术专家
    "普通": 3      # 6% - 孝子节妇、义士、民间知名人物
}

# 性别分布目标
GENDER_RATIO = {
    "男性": 0.7,   # 70%
    "女性": 0.3    # 30%
}

class CharacterListGenerator:
    """人物名单生成器"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent.parent / "data" / "characters"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_comprehensive_list(self) -> Dict[str, Any]:
        """生成完整的1200人物名单"""
        character_list = {}
        character_id = 1
        
        print(f"开始生成24朝代完整人物名单...")
        print(f"目标：每个朝代50人，共计1200人")
        print(f"阶层分布：政治30%、文化30%、社会24%、科技10%、普通6%")
        print(f"性别分布：男性70%、女性30%")
        print(f"-" * 60)
        
        for dynasty, period in DYNASTIES.items():
            print(f"\n生成 {dynasty} 人物名单...")
            dynasty_characters = self.generate_dynasty_characters(dynasty, period)
            
            for char_data in dynasty_characters:
                character_list[str(character_id)] = char_data
                character_id += 1
                
            print(f"  ✓ 已生成 {len(dynasty_characters)} 个人物")
        
        print(f"\n" + "=" * 60)
        print(f"完成！总共生成 {len(character_list)} 个人物")
        
        return character_list
    
    def generate_dynasty_characters(self, dynasty: str, period: str) -> List[Dict[str, str]]:
        """为单个朝代生成50个人物"""
        characters = []
        
        # 按阶层生成人物
        for social_class, count in SOCIAL_CLASSES.items():
            class_characters = self.generate_class_characters(
                dynasty, period, social_class, count
            )
            characters.extend(class_characters)
        
        return characters
    
    def generate_class_characters(self, dynasty: str, period: str, 
                                 social_class: str, count: int) -> List[Dict[str, str]]:
        """为特定阶层生成人物"""
        characters = []
        
        # 计算性别分布
        male_count = int(count * GENDER_RATIO["男性"])
        female_count = count - male_count
        
        # 生成该阶层的代表性人物类型
        character_types = self.get_character_types(social_class, dynasty)
        
        # 生成男性人物
        for i in range(male_count):
            char_type = character_types[i % len(character_types)] if character_types else "著名人物"
            characters.append({
                "name": f"{dynasty}{social_class}{char_type}_{i+1}",  # 占位符，后续替换为真实姓名
                "source": "历史",
                "era": dynasty,
                "social_class": social_class,
                "gender": "男性",
                "character_type": char_type,
                "placeholder": True  # 标记为占位符，需要后续完善
            })
        
        # 生成女性人物
        for i in range(female_count):
            char_type = character_types[i % len(character_types)] if character_types else "著名人物"
            characters.append({
                "name": f"{dynasty}{social_class}{char_type}_女{i+1}",  # 占位符
                "source": "历史",
                "era": dynasty,
                "social_class": social_class,
                "gender": "女性", 
                "character_type": char_type,
                "placeholder": True  # 标记为占位符，需要后续完善
            })
        
        return characters
    
    def get_character_types(self, social_class: str, dynasty: str) -> List[str]:
        """根据阶层和朝代获取人物类型"""
        character_types = {
            "政治": [
                "皇帝", "后妃", "王侯", "宰相", "大臣", 
                "将军", "刺史", "县令", "太监", "外交官",
                "改革家", "谋士", "御史", "尚书", "状元"
            ],
            "文化": [
                "思想家", "哲学家", "文学家", "诗人", "画家",
                "书法家", "音乐家", "学者", "教育家", "史学家",
                "戏剧家", "小说家", "文学家", "宗教领袖", "翻译家"
            ],
            "社会": [
                "商人", "工匠", "医生", "道士", "僧侣",
                "侠客", "农民领袖", "慈善家", "名士", "记者",
                "厨师", "建筑师", "律师", "收藏家", "外交学者"
            ],
            "科技": [
                "科学家", "发明家", "工程师", "天文学家", "数学家",
                "医学家", "农学家", "水利专家", "建筑学家", "技术专家"
            ],
            "普通": [
                "孝子", "节妇", "义士", "烈女", "贤母",
                "忠臣", "孝女", "义仆", "善人", "平民英雄"
            ]
        }
        
        return character_types.get(social_class, ["著名人物"])
    
    def save_character_list(self, character_list: Dict[str, Any], filename: str = "character_list_extended.json"):
        """保存人物名单到文件"""
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(character_list, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ 人物名单已保存到: {output_path}")
        
        # 生成统计报告
        self.generate_statistics_report(character_list, output_path)
        
        return output_path
    
    def generate_statistics_report(self, character_list: Dict[str, Any], output_path: Path):
        """生成统计报告"""
        report = {
            "total_characters": len(character_list),
            "dynasties": {},
            "social_classes": {},
            "gender_distribution": {},
            "placeholders_count": 0
        }
        
        for char_id, char_data in character_list.items():
            # 朝代统计
            dynasty = char_data.get("era", "未知")
            report["dynasties"][dynasty] = report["dynasties"].get(dynasty, 0) + 1
            
            # 阶层统计
            social_class = char_data.get("social_class", "未知")
            report["social_classes"][social_class] = report["social_classes"].get(social_class, 0) + 1
            
            # 性别统计
            gender = char_data.get("gender", "未知")
            report["gender_distribution"][gender] = report["gender_distribution"].get(gender, 0) + 1
            
            # 占位符统计
            if char_data.get("placeholder", False):
                report["placeholders_count"] += 1
        
        # 保存统计报告
        report_path = self.output_dir / "character_statistics.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 统计报告已保存到: {report_path}")
        
        # 打印关键统计
        print(f"\n📊 关键统计信息:")
        print(f"  总人物数: {report['total_characters']}")
        print(f"  朝代覆盖: {len(report['dynasties'])} 个")
        print(f"  占位符: {report['placeholders_count']} 个 (需要后续完善)")
        print(f"  性别分布: 男性 {report['gender_distribution'].get('男性', 0)} 人, 女性 {report['gender_distribution'].get('女性', 0)} 人")

def main():
    """主函数"""
    print("=" * 60)
    print("历史人物库扩充 - 人物名单生成")
    print("=" * 60)
    
    # 创建生成器
    generator = CharacterListGenerator()
    
    # 生成完整名单
    character_list = generator.generate_comprehensive_list()
    
    # 保存到文件
    generator.save_character_list(character_list)
    
    print("\n" + "=" * 60)
    print("人物名单生成完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()