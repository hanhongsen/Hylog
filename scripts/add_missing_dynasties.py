"""
批量补充缺失的汉朝和唐朝人物数据

由于API余额限制，创建手动脚本补充重要历史人物
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

# 汉朝重要人物数据（模拟AI分析结果）
han_characters = [
    {
        "name": "汉武帝",
        "source": "历史",
        "era": "汉朝", 
        "description": "汉武帝刘彻，西汉第七位皇帝，在位期间开疆拓土，独尊儒术，使汉朝达到极盛时期。",
        "ocean_vector": {"O": 0.85, "C": 0.82, "E": 0.78, "A": 0.55, "N": 0.65},
        "tags": ["皇帝", "雄才大略", "开拓进取", "儒家尊崇", "武功极盛"],
        "quote": "寇可往，我亦可往。",
        "personality_keyword": "雄才大略型",
        "classic_events": "1. 下诏罢黜百家，独尊儒术，确立儒家思想统治地位。2. 派遣张骞出使西域，开辟丝绸之路。3. 多次对匈奴用兵，开疆拓土，奠定汉朝疆域基础。",
        "fun_facts": "汉武帝在位54年，是中国历史上在位时间较长的皇帝之一，晚年发生了巫蛊之祸。",
        "advice": "在追求伟大目标时，既要志向远大，也要注意平衡各方关系，避免晚年失误。",
        "related_books": [
            {"title": "《史记·孝武本纪》", "description": "司马迁所著，记录了汉武帝的生平事迹，是研究汉武帝的重要史料。"},
            {"title": "《汉书·武帝纪》", "description": "班固所著，详细记载了汉武帝在位期间的重大政策和事件。"},
            {"title": "《秦汉史》", "description": "现代史学著作，全面分析了汉武帝时期的政治、军事、文化变革。"}
        ]
    },
    {
        "name": "卫青",
        "source": "历史",
        "era": "汉朝",
        "description": "卫青，西汉著名军事家、将领，多次率军击败匈奴，为汉朝开疆拓土立下汗马功劳。",
        "ocean_vector": {"O": 0.72, "C": 0.88, "E": 0.65, "A": 0.75, "N": 0.35},
        "tags": ["军事家", "将领", "抗匈英雄", "忠诚勇武", "谦虚谨慎"],
        "quote": "匈奴未灭，何以家为。",
        "personality_keyword": "忠诚勇武型",
        "classic_events": "1. 率军大败匈奴，收复河套地区。2. 多次出征漠北，重创匈奴主力。3. 谨慎谨慎，从不居功自傲。",
        "fun_facts": "卫青原来是平阳侯家奴，后来成为汉朝大将军，是典型的平民逆袭成功案例。",
        "advice": "出身不重要，重要的是能力和品格。忠诚谨慎，不居功自傲是成功的关键。",
        "related_books": [
            {"title": "《史记·卫将军骠骑列传》", "description": "司马迁所著，记录了卫青、霍去病等汉匈名将的生平事迹。"},
            {"title": "《汉书·卫青霍去病传》", "description": "班固所著，详细记载了卫青等将领抗击匈奴的辉煌战绩。"},
            {"title": "《汉代军事史》", "description": "现代军事史著作，分析了汉朝对匈奴战争的战略战术。"}
        ]
    },
    {
        "name": "霍去病",
        "source": "历史", 
        "era": "汉朝",
        "description": "霍去病，西汉著名军事天才，18岁从军，24岁英年早逝，曾多次深入漠北痛击匈奴。",
        "ocean_vector": {"O": 0.95, "C": 0.65, "E": 0.90, "A": 0.45, "N": 0.55},
        "tags": ["军事天才", "少年英雄", "抗匈名将", "勇猛果断", "英年早逝"],
        "quote": "匈奴未灭，何以家为。",
        "personality_keyword": "英勇果断型", 
        "classic_events": "1. 18岁随军出征，率800骁骑深入大漠，大胜而归。2. 封狼居胥，成为后世武将最高荣誉。3. 24岁英年早逝，留下千古遗憾。",
        "fun_facts": "霍去病是卫青的外甥，18岁就开始征战生涯，用6年时间就做到了大将军高位。",
        "advice": "年轻不是障碍，才华和勇气可以在很短时间内创造辉煌，但也要注意身体健康。",
        "related_books": [
            {"title": "《史记·卫将军骠骑列传》", "description": "司马迁所著，记录了霍去病短暂而辉煌的军事生涯。"},
            {"title": "《汉书·霍去病传》", "description": "详细记载了霍去病的军事成就和英雄事迹。"},
            {"title": "《汉代军事史》", "description": "分析了霍去病的战术特点和军事贡献。"}
        ]
    },
    {
        "name": "吕雉",
        "source": "历史",
        "era": "汉朝",
        "description": "吕雉，汉高祖刘邦皇后，是中国历史上第一位有记载的皇后和皇太后，在刘邦死后掌权十六年。",
        "ocean_vector": {"O": 0.55, "C": 0.75, "E": 0.45, "A": 0.30, "N": 0.70},
        "tags": ["皇后", "皇太后", "权力女性", "政治强人", "冷酷果断"],
        "quote": "人生在世，当如吕后，威震天下。",
        "personality_keyword": "权谋冷酷型",
        "classic_events": "1. 在刘邦统一天下的过程中发挥了重要作用。2. 刘邦死后掌握朝政大权，实行吕氏专权。3. 对刘氏宗室和功臣进行残酷清洗，巩固权力。",
        "fun_facts": "吕后是中国历史上第一位临朝称制的女性，为后世武则天等人铺平了道路。",
        "advice": "权力既可以成就伟业，也可能导致残酷的清洗和悲剧。需要平衡权力与仁慈。",
        "related_books": [
            {"title": "《史记·吕太后本纪》", "description": "司马迁所著，记录了吕后的生平和专权过程。"},
            {"title": "《汉书·外戚传》", "description": "详细记载了吕后及其他汉朝后宫女性的政治活动。"},
            {"title": "《汉代政治史》", "description": "分析了吕后专权对汉朝政治制度的影响。"}
        ]
    },
    {
        "name": "萧何",
        "source": "历史",
        "era": "汉朝", 
        "description": "萧何，西汉开国丞相，刘邦的重要谋士和后勤保障专家，为汉朝建立和巩固立下汗马功劳。",
        "ocean_vector": {"O": 0.70, "C": 0.95, "E": 0.55, "A": 0.85, "N": 0.40},
        "tags": ["丞相", "政治家", "后勤专家", "忠诚可靠", "治国能臣"],
        "quote": "运筹帷幄之中，决胜千里之外。",
        "personality_keyword": "稳重贤明型",
        "classic_events": "1. 主持制定汉朝法律制度，建立汉朝治理框架。2. 推荐韩信为大将，为刘邦赢得楚汉战争。3. 镇守关中，为前线提供充足的后勤保障。",
        "fun_facts": "萧何与刘邦是同乡，在刘邦起兵前就担任县吏，一直忠诚辅佐刘邦。",
        "advice": "成功背后需要默默奉献的人，后勤保障和制度建设同样重要。",
        "related_books": [
            {"title": "《史记·萧相国世家》", "description": "司马迁所著，记录了萧何辅佐刘邦建立汉朝的重要贡献。"},
            {"title": "《汉书·萧何曹参传》", "description": "详细记载了萧何的政治成就和治国经验。"},
            {"title": "《汉代政治制度史》", "description": "分析了萧何制定的汉朝法律制度对后世的影响。"}
        ]
    }
]

# 唐朝重要人物数据（模拟AI分析结果）
tang_characters = [
    {
        "name": "唐玄宗",
        "source": "历史",
        "era": "唐朝",
        "description": "唐玄宗李隆基，唐朝第七位皇帝，在位前期开创开元盛世，后期因安史之乱而衰落。",
        "ocean_vector": {"O": 0.80, "C": 0.55, "E": 0.85, "A": 0.60, "N": 0.75},
        "tags": ["皇帝", "开元盛世", "艺术修养", "晚年昏庸", "安史之乱"],
        "quote": "忆昔开元全盛日，小邑犹藏万家室。",
        "personality_keyword": "艺术才情型",
        "classic_events": "1. 诛杀韦后，拥立父亲睿宗，后继承皇位。2. 前期励精图治，开创开元盛世，唐朝达到顶峰。3. 后期沉溺声色，引发安史之乱，唐朝由盛转衰。",
        "fun_facts": "唐玄宗不仅是皇帝，还是杰出的音乐家和艺术家，精通琵琶和作曲。",
        "advice": "成功需要持续的自律和警惕，晚年的错误可能毁掉一生的成就。",
        "related_books": [
            {"title": "《旧唐书·玄宗本纪》", "description": "详细记载了唐玄宗在位期间的重大事件和政策。"},
            {"title": "《新唐书·玄宗本纪》", "description": "重新编写的唐玄宗本纪，评价更加客观全面。"},
            {"title": "《安禄山事迹》", "description": "记载了安史之乱的起因和过程，分析了唐玄宗晚年的失误。"}
        ]
    },
    {
        "name": "魏征",
        "source": "历史",
        "era": "唐朝",
        "description": "魏征，唐朝著名宰相，以直言进谏著称，被称为'诤臣'，辅佐唐太宗开创贞观之治。",
        "ocean_vector": {"O": 0.65, "C": 0.88, "E": 0.45, "A": 0.82, "N": 0.50},
        "tags": ["宰相", "诤臣", "直言敢谏", "忠诚正直", "治国能臣"],
        "quote": "以铜为镜，可以正衣冠；以古为镜，可以知兴替；以人为镜，可以明得失。",
        "personality_keyword": "正直谏言型",
        "classic_events": "1. 曾是太子李建成的谋士，后归顺李世民，直言不讳。2. 多次向唐太宗进谏，纠正政策偏差。3. 去世后唐太宗痛失'以人为镜'的谏臣。",
        "fun_facts": "魏征曾是李世民政敌的谋士，但李世民欣赏他的才华和正直，重用他为宰相。",
        "advice": "直言不讳需要勇气和智慧，领导者也应该虚心接受批评建议。",
        "related_books": [
            {"title": "《旧唐书·魏征传》", "description": "记载了魏征的生平和进谏事迹。"},
            {"title": "《贞观政要》", "description": "记录了唐太宗和魏征等人的政治对话，是研究贞观之治的重要资料。"},
            {"title": "《谏太宗十思疏》", "description": "魏征的著名谏书，体现了他的政治智慧和直言风格。"}
        ]
    },
    {
        "name": "房玄龄",
        "source": "历史",
        "era": "唐朝",
        "description": "房玄龄，唐朝著名宰相，唐太宗的重要谋士，参与策划玄武门之变，为贞观之治做出重要贡献。",
        "ocean_vector": {"O": 0.72, "C": 0.92, "E": 0.55, "A": 0.88, "N": 0.45},
        "tags": ["宰相", "谋士", "忠诚稳重", "善于谋划", "治国能臣"],
        "quote": "海纳百川，有容乃大。",
        "personality_keyword": "稳重贤明型",
        "classic_events": "1. 早年投奔李世民，成为重要谋士。2. 参与策划玄武门之变，帮助李世民夺得皇位。3. 担任宰相多年，协助唐太宗治理国家，开创贞观之治。",
        "fun_facts": "房玄龄与杜如晦被称为'房谋杜断'，是唐朝著名的宰相搭档。",
        "advice": "成功需要团队合作，每个人都有自己的专长，合理分工才能取得最大成就。",
        "related_books": [
            {"title": "《旧唐书·房玄龄传》", "description": "记载了房玄龄的生平和政治成就。"},
            {"title": "《贞观政要》", "description": "记录了房玄龄等人的政治活动和治国理念。"},
            {"title": "《唐代宰相制度研究》", "description": "分析了房玄龄等宰相在唐朝政治制度中的作用。"}
        ]
    },
    {
        "name": "杜如晦",
        "source": "历史",
        "era": "唐朝",
        "description": "杜如晦，唐朝著名宰相，与房玄龄并称'房谋杜断'，是唐太宗的重要辅佐大臣。",
        "ocean_vector": {"O": 0.78, "C": 0.90, "E": 0.50, "A": 0.75, "N": 0.55},
        "tags": ["宰相", "决断力强", "善于分析", "忠诚可靠", "治国能臣"],
        "quote": "断大事，不拘小节。",
        "personality_keyword": "果断决策型",
        "classic_events": "1. 早年投奔李世民，展现出色的政治才能。2. 与房玄龄配合默契，'房谋杜断'成为佳话。3. 在关键时刻帮助唐太宗做出正确决策，巩固政权。",
        "fun_facts": "杜如晦英年早逝，唐太宗非常悲痛，废朝五日以示哀悼。",
        "advice": "决断力是领导者的关键素质，需要在关键时刻做出正确决定。",
        "related_books": [
            {"title": "《旧唐书·杜如晦传》", "description": "记载了杜如晦的生平和政治决断能力。"},
            {"title": "《贞观政要》", "description": "记录了杜如晦等人在重大决策中的作用。"},
            {"title": "《唐代政治史》", "description": "分析了'房谋杜断'在贞观之治中的作用。"}
        ]
    },
    {
        "name": "长孙无忌",
        "source": "历史",
        "era": "唐朝",
        "description": "长孙无忌，唐朝著名宰相和外戚，唐太宗的妻兄，曾参与玄武门之变，后受命编撰《唐律疏议》。",
        "ocean_vector": {"O": 0.60, "C": 0.85, "E": 0.50, "A": 0.65, "N": 0.60},
        "tags": ["宰相", "外戚", "法典编撰", "忠诚可靠", "权势显赫"],
        "quote": "法者，治之端也。",
        "personality_keyword": "严谨法治型",
        "classic_events": "1. 参与策划玄武门之变，帮助李世民夺得皇位。2. 担任宰相多年，权势显赫。3. 主持编撰《唐律疏议》，成为古代法典典范。",
        "fun_facts": "长孙无忌既是唐太宗的妻兄，又是重臣，这种双重身份让他既受信任又容易受到猜忌。",
        "advice": "在权力和信任之间需要保持平衡，法治和制度比个人关系更重要。",
        "related_books": [
            {"title": "《旧唐书·长孙无忌传》", "description": "记载了长孙无忌的生平和政治成就。"},
            {"title": "《唐律疏议》", "description": "长孙无忌主持编撰的法典，是中国古代法律的集大成之作。"},
            {"title": "《唐代法律制度史》", "description": "分析了长孙无忌在唐朝法律建设中的重要作用。"}
        ]
    }
]

def add_characters(characters_data, era_name):
    """添加人物数据到数据库"""
    print(f"{'='*60}")
    print(f"添加{era_name}人物数据")
    print(f"{'='*60}")
    
    # 初始化数据库
    engine = create_engine(f"sqlite:///{DATABASE_FILE}")
    create_tables(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    added_count = 0
    skipped_count = 0
    
    for char_data in characters_data:
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
    print(f"\n{'='*60}")
    print(f"{era_name}人物添加完成")
    print(f"{'='*60}")
    print(f"成功添加：{added_count} 人")
    print(f"跳过已存在：{skipped_count} 人")
    print(f"{'='*60}\n")

def main():
    """主函数"""
    print("🎯 开始补充汉朝和唐朝重要人物数据")
    
    # 添加汉朝人物
    add_characters(han_characters, "汉朝")
    
    # 添加唐朝人物  
    add_characters(tang_characters, "唐朝")
    
    print("✅ 汉朝和唐朝人物数据补充完成！")

if __name__ == "__main__":
    main()