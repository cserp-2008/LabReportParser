import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser
from parser.jph_parser import JPHParser

file_path = "D:\\private\\CS\\CS\\src\\storage\\report\\2026\\07\\a7383d85e981444cb5e816573fa74973_2026-05-08肿瘤标志物.pdf"

if os.path.exists(file_path):
    pdf_parser = PDFParser()
    jph_parser = JPHParser()
    
    pages = pdf_parser.parse(file_path)
    if pages:
        full_coords_text = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)
        print("=== OCR坐标数据 ===")
        lines = full_coords_text.split("\n")
        for i, line in enumerate(lines):
            print(f"{i}: {line}")
        
        parsed = jph_parser.parse(full_coords_text)
        print(f"\n=== 解析结果 ===")
        for r in parsed.results:
            print(f"    {r.code} | {r.raw_item_name} = {r.raw_value} {r.unit} ref={r.reference_text}")
            
        print(f"\n=== 原始items ===")
        ocr_items = jph_parser._parse_ocr_text(full_coords_text)
        items = jph_parser._parse_table_from_coords(ocr_items)
        for item in items:
            print(f"    code={item['code']} name={item['name']} result={item['result']} unit={item['unit']} ref={item['ref_range']}")
else:
    print(f"文件不存在: {file_path}")
