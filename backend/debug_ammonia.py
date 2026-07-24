import sys
import glob
sys.path.insert(0, 'D:/private/CS/CS/src/backend')

from parser.pdf_parser import PDFParser
from parser.jph_parser import JPHParser

files = glob.glob("D:/private/CS/CS/src/storage/report/2026/07/*血氨*.pdf")
if files:
    file_path = files[0]
    print(f"=== 血氨测定报告 ===")
    print(f"文件: {file_path}")
    
    pdf_parser = PDFParser()
    pages = pdf_parser.parse(file_path)
    
    if pages:
        coords_text = pages[0].ocr_coords_text
        
        parser = JPHParser()
        ocr_items = parser._parse_ocr_text(coords_text)
        header_items = [i for i in ocr_items if parser._is_header_text(i["text"])]
        boundaries = parser._detect_column_boundaries(header_items)
        
        print(f"边界检测结果:")
        print(f"  code_end={boundaries['code']}, name_end={boundaries['name']}")
        print(f"  result_start={boundaries['result']}, unit_start={boundaries['unit']}")
        print(f"  ref_start={boundaries['ref_range']}")
        
        min_y = max(i["y"] for i in header_items) + 10
        max_y = min(i["y"] for i in header_items) + 800
        data_items = [i for i in ocr_items if min_y < i["y"] < max_y and not parser._is_header_text(i["text"])]
        
        print(f"\n数据行:")
        rows = parser._group_by_row(data_items)
        for idx, row in enumerate(rows):
            print(f"  行 {idx}:")
            for i in row:
                print(f"    x={i['x']:.0f}, text={i['text']}")
        
        print(f"\n逐行解析过程:")
        for idx, row in enumerate(rows):
            item = {"code": "", "name": "", "result": "", "unit": "", "ref_range": ""}
            code_end = boundaries["code"]
            name_end = boundaries["name"]
            result_start = boundaries["result"]
            unit_start = boundaries["unit"]
            ref_start = boundaries["ref_range"]
            
            for i in row:
                if i["x"] < code_end:
                    if re.match(r"^[A-Z0-9/\-._]+$", i["text"]) and len(i["text"]) <= 15:
                        item["code"] = i["text"]
                    else:
                        item["name"] += i["text"]
                    print(f"      x={i['x']:.0f} < {code_end:.0f} -> code/name: {i['text']}")
                elif i["x"] < name_end:
                    item["name"] += i["text"]
                    print(f"      {code_end:.0f} <= x={i['x']:.0f} < {name_end:.0f} -> name: {i['text']}")
                elif i["x"] < unit_start:
                    print(f"      {name_end:.0f} <= x={i['x']:.0f} < {unit_start:.0f} -> result: {i['text']}")
                    item["result"] += i["text"]
                elif i["x"] < ref_start:
                    print(f"      {unit_start:.0f} <= x={i['x']:.0f} < {ref_start:.0f} -> unit: {i['text']}")
                    item["unit"] += i["text"]
                else:
                    print(f"      x={i['x']:.0f} >= {ref_start:.0f} -> ref: {i['text']}")
                    item["ref_range"] += i["text"]
            
            print(f"    解析后: code={item['code']}, name={item['name']}, result={item['result']}, unit={item['unit']}, ref={item['ref_range']}")
            parser._clean_item(item)
            print(f"    清理后: code={item['code']}, name={item['name']}, result={item['result']}, unit={item['unit']}, ref={item['ref_range']}")
    else:
        print("无法解析PDF")
