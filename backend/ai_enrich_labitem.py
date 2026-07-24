"""使用大模型补全标准指标库中的缩写、英文名、分类等信息"""
import os
import sys
import json
import time
import httpx
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import LabItem, AIConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

engine = create_engine('sqlite:///labreport.db')
Session = sessionmaker(bind=engine)
db = Session()

# 获取AI配置
config = db.query(AIConfig).filter(AIConfig.is_active == 1).first()
if not config:
    print("错误：AI配置未设置，请先在系统中配置API Key")
    sys.exit(1)

client = httpx.Client(
    base_url=config.base_url,
    headers={"Authorization": f"Bearer {config.api_key}"},
    timeout=300.0
)

def enrich_item(item: LabItem):
    """使用大模型补全单个指标的信息"""
    prompt = f"""你是一个专业的医学指标知识助手。请根据以下化验指标名称，补全相关信息。

指标名称：{item.item_name}

请返回JSON格式，包含以下字段：
- abbr: 标准缩写（如 WBC、ALT、GLU），如果没有缩写请返回null
- english_name: 英文名称（如 White Blood Cell count），如果没有请返回null
- category: 分类（从以下选择：血常规、肝功能、肾功能、血糖、血脂、电解质、甲状腺、凝血功能、心肌酶、免疫、肿瘤标志物、炎症标志物、传染病、药敏、微生物、尿常规、便常规、血型、胰酶、其他）
- standard_unit: 标准单位（如 g/L、U/L、mmol/L），如果没有请返回null
- reference_range: 标准参考范围（如 3.5-9.5），如果没有请返回null

请直接返回JSON，不要有任何解释或额外文字！"""

    try:
        response = client.post(
            "/chat/completions",
            json={
                "model": "doubao-seed-2-1-pro-260628",
                "messages": [{
                    "role": "user",
                    "content": prompt
                }],
                "response_format": {"type": "json_object"},
                "max_tokens": 500,
                "temperature": 0.1
            }
        )
        response.raise_for_status()
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        data = json.loads(content)
        
        return {
            "abbr": data.get("abbr"),
            "english_name": data.get("english_name"),
            "category": data.get("category"),
            "standard_unit": data.get("standard_unit"),
            "reference_range": data.get("reference_range")
        }
    except Exception as e:
        logger.error(f"调用大模型失败: {e}")
        return None

# 获取需要补全的指标
items = db.query(LabItem).filter(
    (LabItem.abbr.is_(None)) | (LabItem.abbr == "") |
    (LabItem.english_name.is_(None)) | (LabItem.english_name == "") |
    (LabItem.category == "其他") | (LabItem.category.is_(None)) |
    (LabItem.standard_unit.is_(None)) | (LabItem.standard_unit == "") |
    (LabItem.reference_range.is_(None)) | (LabItem.reference_range == "")
).all()

print(f"需要补全的指标数: {len(items)}")

success_count = 0
fail_count = 0

for idx, item in enumerate(items, 1):
    print(f"\n[{idx}/{len(items)}] 处理: {item.item_name}")
    
    result = enrich_item(item)
    if result:
        updated = False
        
        if not item.abbr and result.get("abbr"):
            item.abbr = result["abbr"]
            print(f"  补全缩写: {result['abbr']}")
            updated = True
            
        if not item.english_name and result.get("english_name"):
            item.english_name = result["english_name"]
            print(f"  补全英文名: {result['english_name']}")
            updated = True
            
        if (not item.category or item.category == "其他") and result.get("category"):
            item.category = result["category"]
            print(f"  补全分类: {result['category']}")
            updated = True
            
        if not item.standard_unit and result.get("standard_unit"):
            item.standard_unit = result["standard_unit"]
            print(f"  补全单位: {result['standard_unit']}")
            updated = True
            
        if not item.reference_range and result.get("reference_range"):
            item.reference_range = result["reference_range"]
            print(f"  补全参考范围: {result['reference_range']}")
            updated = True
        
        if updated:
            success_count += 1
        else:
            print("  无更新")
    else:
        fail_count += 1
        print("  失败")
    
    if idx % 10 == 0:
        db.commit()
        print(f"\n已提交 {idx} 条...")
    
    time.sleep(0.5)

db.commit()

print("\n" + "=" * 60)
print("补全完成")
print("=" * 60)
print(f"成功: {success_count} 条")
print(f"失败: {fail_count} 条")

# 最终统计
total = db.query(LabItem).count()
with_abbr = db.query(LabItem).filter(LabItem.abbr.isnot(None), LabItem.abbr != "").count()
with_eng = db.query(LabItem).filter(LabItem.english_name.isnot(None), LabItem.english_name != "").count()
with_cat = db.query(LabItem).filter(LabItem.category.isnot(None), LabItem.category != "").count()
with_unit = db.query(LabItem).filter(LabItem.standard_unit.isnot(None), LabItem.standard_unit != "").count()
with_ref = db.query(LabItem).filter(LabItem.reference_range.isnot(None), LabItem.reference_range != "").count()

print(f"\n标准指标总数: {total}")
print(f"  有缩写: {with_abbr} ({with_abbr/total*100:.1f}%)")
print(f"  有英文名: {with_eng} ({with_eng/total*100:.1f}%)")
print(f"  有分类: {with_cat} ({with_cat/total*100:.1f}%)")
print(f"  有单位: {with_unit} ({with_unit/total*100:.1f}%)")
print(f"  有参考范围: {with_ref} ({with_ref/total*100:.1f}%)")

db.close()
