import sys
import re
sys.path.insert(0, 'D:/private/CS/CS/src/backend')

from parser.jph_parser import JPHParser, UNIT_PATTERN

parser = JPHParser()

ocr_items = [
    {"x": 81, "y": 637, "text": "9CREA*△肌酐(干化学法)"},
    {"x": 501, "y": 641, "text": "87.1"},
    {"x": 589, "y": 639, "text": "μmol/L 58. 0--110.0"},
]

print("测试肌酐行解析:")
for i in ocr_items:
    print(f"  x={i['x']} y={i['y']} text='{i['text']}'")

item = {"code": "", "name": "", "result": "", "unit": "", "ref_range": ""}

for i in ocr_items:
    x = i["x"]
    text = i["text"]
    
    if x < 170:
        print(f"  -> code/name区域: '{text}'")
        if re.match(r"^[A-Z0-9/\-._]+$", text) and len(text) <= 15:
            item["code"] = text
        else:
            item["name"] += text
    elif x < 465:
        print(f"  -> name区域: '{text}'")
        item["name"] += text
    elif x < 560:
        print(f"  -> result区域: '{text}'")
        if re.search(UNIT_PATTERN, text):
            parser._parse_merged_cell(text, item)
        elif re.search(r"[-~—–≤≥]", text):
            item["ref_range"] += text
        else:
            item["result"] += text
    elif x < 650:
        print(f"  -> unit区域: '{text}'")
        if re.match(r"^[↑↓].*" + UNIT_PATTERN, text):
            arrow_match = re.match(r"^([↑↓])(.*)", text)
            if arrow_match:
                item["result"] += arrow_match.group(1)
                text = arrow_match.group(2)
        
        if re.search(r"--|[-~—–≤≥]", text):
            ref_patterns = [
                r"(\d+[\d.\s]*--[\d.\s]+\d)",
                r"(\d+\.?\d*\s*[-~—–]\s*\d+\.?\d*)",
                r"([≤≥<>]\s*\d+\.?\d*)",
            ]
            ref_match = None
            for pattern in ref_patterns:
                ref_match = re.search(pattern, text)
                if ref_match:
                    break
            if ref_match:
                ref_part = ref_match.group(1).replace(" ", "")
                print(f"     -> 提取参考范围: '{ref_part}'")
                text = text[:ref_match.start()]
                if not item["ref_range"]:
                    item["ref_range"] = ref_part
        
        item["unit"] += text
    else:
        print(f"  -> ref_range区域: '{text}'")
        item["ref_range"] += text

print(f"\n解析结果:")
print(f"  code: '{item['code']}'")
print(f"  name: '{item['name']}'")
print(f"  result: '{item['result']}'")
print(f"  unit: '{item['unit']}'")
print(f"  ref_range: '{item['ref_range']}'")
