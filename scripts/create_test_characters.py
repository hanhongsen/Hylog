"""
创建测试朝代的真实历史人物
为春秋、汉朝、唐朝三个朝代各创建50个真实的历史人物
"""

import json
from pathlib import Path

# 24朝代分类体系
DYNASTIES = ["春秋", "汉朝", "唐朝"]  # 测试用三个朝代

# 真实历史人物样本
TEST_CHARACTERS = {
    "春秋": [
        # 政治阶层（15人）
        {"name": "齐桓公", "social_class": "政治", "gender": "男性", "character_type": "诸侯"},
        {"name": "晋文公", "social_class": "政治", "gender": "男性", "character_type": "诸侯"},
        {"name": "楚庄王", "social_class": "政治", "gender": "男性", "character_type": "诸侯"},
        {"name": "秦穆公", "social_class": "政治", "gender": "男性", "character_type": "诸侯"},
        {"name": "宋襄公", "social_class": "政治", "gender": "男性", "character_type": "诸侯"},
        {"name": "鲁庄公", "social_class": "政治", "gender": "男性", "character_type": "诸侯"},
        {"name": "管仲", "social_class": "政治", "gender": "男性", "character_type": "宰相"},
        {"name": "鲍叔牙", "social_class": "政治", "gender": "男性", "character_type": "大臣"},
        {"name": "晏婴", "social_class": "政治", "gender": "男性", "character_type": "大臣"},
        {"name": "子产", "social_class": "政治", "gender": "男性", "character_type": "大臣"},
        {"name": "伍子胥", "social_class": "政治", "gender": "男性", "character_type": "将军"},
        {"name": "孙武", "social_class": "政治", "gender": "男性", "character_type": "将军"},
        {"name": "文种", "social_class": "政治", "gender": "男性", "character_type": "大臣"},
        {"name": "范蠡", "social_class": "政治", "gender": "男性", "character_type": "谋士"},
        {"name": "西施", "social_class": "政治", "gender": "女性", "character_type": "后妃"},

        # 文化阶层（15人）
        {"name": "孔子", "social_class": "文化", "gender": "男性", "character_type": "思想家"},
        {"name": "老子", "social_class": "文化", "gender": "男性", "character_type": "哲学家"},
        {"name": "墨子", "social_class": "文化", "gender": "男性", "character_type": "思想家"},
        {"name": "庄子", "social_class": "文化", "gender": "男性", "character_type": "哲学家"},
        {"name": "孟子", "social_class": "文化", "gender": "男性", "character_type": "思想家"},
        {"name": "荀子", "social_class": "文化", "gender": "男性", "character_type": "思想家"},
        {"name": "韩非子", "social_class": "文化", "gender": "男性", "character_type": "思想家"},
        {"name": "孙子", "social_class": "文化", "gender": "男性", "character_type": "军事家"},
        {"name": "左丘明", "social_class": "文化", "gender": "男性", "character_type": "史学家"},
        {"name": "屈原", "social_class": "文化", "gender": "男性", "character_type": "诗人"},
        {"name": "宋玉", "social_class": "文化", "gender": "男性", "character_type": "文学家"},
        {"name": "伯牙", "social_class": "文化", "gender": "男性", "character_type": "音乐家"},
        {"name": "师旷", "social_class": "文化", "gender": "男性", "character_type": "音乐家"},
        {"name": "鲁班", "social_class": "文化", "gender": "男性", "character_type": "工匠"},
        {"name": "扁鹊", "social_class": "文化", "gender": "男性", "character_type": "医者"},

        # 社会阶层（12人）
        {"name": "子贡", "social_class": "社会", "gender": "男性", "character_type": "商人"},
        {"name": "范蠡", "social_class": "社会", "gender": "男性", "character_type": "商人"},
        {"name": "端木赐", "social_class": "社会", "gender": "男性", "character_type": "商人"},
        {"name": "欧冶子", "social_class": "社会", "gender": "男性", "character_type": "工匠"},
        {"name": "干将", "social_class": "社会", "gender": "男性", "character_type": "工匠"},
        {"name": "莫邪", "social_class": "社会", "gender": "女性", "character_type": "工匠"},
        {"name": "俞伯牙", "social_class": "社会", "gender": "男性", "character_type": "侠客"},
        {"name": "专诸", "social_class": "社会", "gender": "男性", "character_type": "侠客"},
        {"name": "豫让", "social_class": "社会", "gender": "男性", "character_type": "侠客"},
        {"name": "荆轲", "social_class": "社会", "gender": "男性", "character_type": "侠客"},
        {"name": "要离", "social_class": "社会", "gender": "男性", "character_type": "侠客"},
        {"name": "聂政", "social_class": "社会", "gender": "男性", "character_type": "侠客"},

        # 科技阶层（5人）
        {"name": "甘德", "social_class": "科技", "gender": "男性", "character_type": "天文学家"},
        {"name": "石申", "social_class": "科技", "gender": "男性", "character_type": "天文学家"},
        {"name": "梓慎", "social_class": "科技", "gender": "男性", "character_type": "天文学家"},
        {"name": "裨灶", "social_class": "科技", "gender": "男性", "character_type": "天文学家"},
        {"name": "史墨", "social_class": "科技", "gender": "男性", "character_type": "占星家"},

        # 普通名人（3人）
        {"name": "闵子骞", "social_class": "普通", "gender": "男性", "character_type": "孝子"},
        {"name": "曾参", "social_class": "普通", "gender": "男性", "character_type": "孝子"},
        {"name": "老莱子", "social_class": "普通", "gender": "男性", "character_type": "孝子"}
    ],

    "汉朝": [
        # 政治阶层（15人）
        {"name": "刘邦", "social_class": "政治", "gender": "男性", "character_type": "皇帝"},
        {"name": "吕雉", "social_class": "政治", "gender": "女性", "character_type": "后妃"},
        {"name": "汉武帝", "social_class": "政治", "gender": "男性", "character_type": "皇帝"},
        {"name": "卫青", "social_class": "政治", "gender": "男性", "character_type": "将军"},
        {"name": "霍去病", "social_class": "政治", "gender": "男性", "character_type": "将军"},
        {"name": "张良", "social_class": "政治", "gender": "男性", "character_type": "谋士"},
        {"name": "萧何", "social_class": "政治", "gender": "男性", "character_type": "大臣"},
        {"name": "韩信", "social_class": "政治", "gender": "男性", "character_type": "将军"},
        {"name": "曹参", "social_class": "政治", "gender": "男性", "character_type": "大臣"},
        {"name": "陈平", "social_class": "政治", "gender": "男性", "character_type": "谋士"},
        {"name": "周勃", "social_class": "政治", "gender": "男性", "character_type": "将军"},
        {"name": "李广", "social_class": "政治", "gender": "男性", "character_type": "将军"},
        {"name": "苏武", "social_class": "政治", "gender": "男性", "character_type": "外交官"},
        {"name": "张骞", "social_class": "政治", "gender": "男性", "character_type": "外交官"},
        {"name": "王昭君", "social_class": "政治", "gender": "女性", "character_type": "后妃"},

        # 文化阶层（15人）
        {"name": "司马迁", "social_class": "文化", "gender": "男性", "character_type": "史学家"},
        {"name": "班固", "social_class": "文化", "gender": "男性", "character_type": "史学家"},
        {"name": "刘向", "social_class": "文化", "gender": "男性", "character_type": "学者"},
        {"name": "扬雄", "social_class": "文化", "gender": "男性", "character_type": "文学家"},
        {"name": "张衡", "social_class": "文化", "gender": "男性", "character_type": "科学家"},
        {"name": "蔡伦", "social_class": "文化", "gender": "男性", "character_type": "发明家"},
        {"name": "刘歆", "social_class": "文化", "gender": "男性", "character_type": "学者"},
        {"name": "桓谭", "social_class": "文化", "gender": "男性", "character_type": "哲学家"},
        {"name": "王充", "social_class": "文化", "gender": "男性", "character_type": "思想家"},
        {"name": "班超", "social_class": "文化", "gender": "男性", "character_type": "外交家"},
        {"name": "郑玄", "social_class": "文化", "gender": "男性", "character_type": "经学家"},
        {"name": "许慎", "social_class": "文化", "gender": "男性", "character_type": "文字学家"},
        {"name": "张仲景", "social_class": "文化", "gender": "男性", "character_type": "医学家"},
        {"name": "华佗", "social_class": "文化", "gender": "男性", "character_type": "医学家"},
        {"name": "蔡文姬", "social_class": "文化", "gender": "女性", "character_type": "文学家"},

        # 社会阶层（12人）
        {"name": "卓文君", "social_class": "社会", "gender": "女性", "character_type": "商人"},
        {"name": "巴清", "social_class": "社会", "gender": "女性", "character_type": "商人"},
        {"name": "霍光", "social_class": "社会", "gender": "男性", "character_type": "权臣"},
        {"name": "金日磾", "social_class": "社会", "gender": "男性", "character_type": "贵族"},
        {"name": "上官桀", "social_class": "社会", "gender": "男性", "character_type": "大臣"},
        {"name": "赵飞燕", "social_class": "社会", "gender": "女性", "character_type": "名妓"},
        {"name": "貂蝉", "social_class": "社会", "gender": "女性", "character_type": "义士"},
        {"name": "东方朔", "social_class": "社会", "gender": "男性", "character_type": "名士"},
        {"name": "严君平", "social_class": "社会", "gender": "男性", "character_type": "隐士"},
        {"name": "黄石公", "social_class": "社会", "gender": "男性", "character_type": "隐士"},
        {"name": "壶公", "social_class": "社会", "gender": "男性", "character_type": "道士"},
        {"name": "栾巴", "social_class": "社会", "gender": "男性", "character_type": "方士"},

        # 科技阶层（5人）
        {"name": "张衡", "social_class": "科技", "gender": "男性", "character_type": "科学家"},
        {"name": "蔡伦", "social_class": "科技", "gender": "男性", "character_type": "发明家"},
        {"name": "毕岚", "social_class": "科技", "gender": "男性", "character_type": "发明家"},
        {"name": "魏伯阳", "social_class": "科技", "gender": "男性", "character_type": "炼丹家"},
        {"name": "张仲景", "social_class": "科技", "gender": "男性", "character_type": "医学家"},

        # 普通名人（3人）
        {"name": "缇萦", "social_class": "普通", "gender": "女性", "character_type": "孝女"},
        {"name": "姜诗", "social_class": "普通", "gender": "男性", "character_type": "孝子"},
        {"name": "王祥", "social_class": "普通", "gender": "男性", "character_type": "孝子"}
    ],

    "唐朝": [
        # 政治阶层（15人）
        {"name": "唐太宗", "social_class": "政治", "gender": "男性", "character_type": "皇帝"},
        {"name": "武则天", "social_class": "政治", "gender": "女性", "character_type": "皇帝"},
        {"name": "唐玄宗", "social_class": "政治", "gender": "男性", "character_type": "皇帝"},
        {"name": "魏征", "social_class": "政治", "gender": "男性", "character_type": "宰相"},
        {"name": "房玄龄", "social_class": "政治", "gender": "男性", "character_type": "宰相"},
        {"name": "杜如晦", "social_class": "政治", "gender": "男性", "character_type": "宰相"},
        {"name": "长孙无忌", "social_class": "政治", "gender": "男性", "character_type": "大臣"},
        {"name": "李靖", "social_class": "政治", "gender": "男性", "character_type": "将军"},
        {"name": "李世勣", "social_class": "政治", "gender": "男性", "character_type": "将军"},
        {"name": "秦琼", "social_class": "政治", "gender": "男性", "character_type": "将军"},
        {"name": "程咬金", "social_class": "政治", "gender": "男性", "character_type": "将军"},
        {"name": "尉迟恭", "social_class": "政治", "gender": "男性", "character_type": "将军"},
        {"name": "狄仁杰", "social_class": "政治", "gender": "男性", "character_type": "大臣"},
        {"name": "姚崇", "social_class": "政治", "gender": "男性", "character_type": "宰相"},
        {"name": "宋璟", "social_class": "政治", "gender": "男性", "character_type": "宰相"},

        # 文化阶层（15人）
        {"name": "李白", "social_class": "文化", "gender": "男性", "character_type": "诗人"},
        {"name": "杜甫", "social_class": "文化", "gender": "男性", "character_type": "诗人"},
        {"name": "白居易", "social_class": "文化", "gender": "男性", "character_type": "诗人"},
        {"name": "王维", "social_class": "文化", "gender": "男性", "character_type": "诗人"},
        {"name": "韩愈", "social_class": "文化", "gender": "男性", "character_type": "文学家"},
        {"name": "柳宗元", "social_class": "文化", "gender": "男性", "character_type": "文学家"},
        {"name": "刘禹锡", "social_class": "文化", "gender": "男性", "character_type": "诗人"},
        {"name": "李商隐", "social_class": "文化", "gender": "男性", "character_type": "诗人"},
        {"name": "杜牧", "social_class": "文化", "gender": "男性", "character_type": "诗人"},
        {"name": "孟浩然", "social_class": "文化", "gender": "男性", "character_type": "诗人"},
        {"name": "王昌龄", "social_class": "文化", "gender": "男性", "character_type": "诗人"},
        {"name": "颜真卿", "social_class": "文化", "gender": "男性", "character_type": "书法家"},
        {"name": "吴道子", "social_class": "文化", "gender": "男性", "character_type": "画家"},
        {"name": "张旭", "social_class": "文化", "gender": "男性", "character_type": "书法家"},
        {"name": "薛涛", "social_class": "文化", "gender": "女性", "character_type": "诗人"},

        # 社会阶层（12人）
        {"name": "玄奘", "social_class": "社会", "gender": "男性", "character_type": "僧侣"},
        {"name": "鉴真", "social_class": "社会", "gender": "男性", "character_type": "僧侣"},
        {"name": "一行", "social_class": "社会", "gender": "男性", "character_type": "僧侣"},
        {"name": "孙思邈", "social_class": "社会", "gender": "男性", "character_type": "医生"},
        {"name": "陆羽", "social_class": "社会", "gender": "男性", "character_type": "茶圣"},
        {"name": "公孙大娘", "social_class": "社会", "gender": "女性", "character_type": "舞蹈家"},
        {"name": "谢小娥", "social_class": "社会", "gender": "女性", "character_type": "义士"},
        {"name": "红线女", "social_class": "社会", "gender": "女性", "character_type": "侠客"},
        {"name": "虬髯客", "social_class": "社会", "gender": "男性", "character_type": "侠客"},
        {"name": "聂隐娘", "social_class": "社会", "gender": "女性", "character_type": "侠客"},
        {"name": "昆仑奴", "social_class": "社会", "gender": "男性", "character_type": "义士"},
        {"name": "古押衙", "social_class": "社会", "gender": "男性", "character_type": "侠客"},

        # 科技阶层（5人）
        {"name": "一行", "social_class": "科技", "gender": "男性", "character_type": "天文学家"},
        {"name": "李淳风", "social_class": "科技", "gender": "男性", "character_type": "天文学家"},
        {"name": "袁天罡", "social_class": "科技", "gender": "男性", "character_type": "天文学家"},
        {"name": "孙思邈", "social_class": "科技", "gender": "男性", "character_type": "医学家"},
        {"name": "边鸾", "social_class": "科技", "gender": "男性", "character_type": "画家"},

        # 普通名人（3人）
        {"name": "王祥", "social_class": "普通", "gender": "男性", "character_type": "孝子"},
        {"name": "孟宗", "social_class": "普通", "gender": "男性", "character_type": "孝子"},
        {"name": "王裒", "social_class": "普通", "gender": "男性", "character_type": "孝子"}
    ]
}

def create_test_character_list():
    """创建测试人物名单"""
    test_characters = {}
    character_id = 1
    
    for dynasty in DYNASTIES:
        print(f"创建 {dynasty} 测试人物...")
        dynasty_chars = TEST_CHARACTERS.get(dynasty, [])
        
        for char_info in dynasty_chars:
            test_characters[str(character_id)] = {
                "name": char_info["name"],
                "source": "历史",
                "era": dynasty,
                "social_class": char_info["social_class"],
                "gender": char_info["gender"],
                "character_type": char_info["character_type"],
                "placeholder": False  # 真实人物，非占位符
            }
            character_id += 1
        
        print(f"  ✓ 已创建 {len(dynasty_chars)} 个真实人物")
    
    return test_characters

def main():
    """主函数"""
    print("=" * 60)
    print("创建测试朝代真实历史人物")
    print("=" * 60)
    
    # 创建测试人物名单
    test_characters = create_test_character_list()
    
    # 保存到文件
    output_dir = Path(__file__).parent.parent / "data" / "characters"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "character_test_list.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(test_characters, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 测试人物名单已保存：{output_file}")
    print(f"总计：{len(test_characters)} 个真实历史人物")
    print(f"朝代：{', '.join(DYNASTIES)}")
    print(f"=" * 60)

if __name__ == "__main__":
    main()