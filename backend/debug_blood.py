import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser
from parser.jph_parser import JPHParser

file_path = "D:\\private\\CS\\CS\\src\\storage\\report\\2026\\07\\f94156de35cd4a778a9910606ee1ee55_2026-05-08血常规.pdf"

if os.path.exists(file_path):
    print(f"文件存在: {file_path}")
else:
    files = Glob("**/*血常规*", "d:\\private\\CS\\CS\\src\\storage")
    for f in files:
        if "2026-05-08" in f:
            file_path = f
            break
    print(f"使用文件: {file_path}")

if os.path.exists(file_path):
    pdf_parser = PDFParser()
    jph_parser = JPHParser()
    
    pages = pdf_parser.parse(file_path)
    if pages:
        full_coords_text = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)
        print("=== OCR坐标数据（前80行）===")
        lines = full_coords_text.split("\n")
        for i, line in enumerate(lines[:80]):
            print(f"{i}: {line}")
        
        parsed = jph_parser.parse(full_coords_text)
        print(f"\n=== 解析结果 ===")
        for r in parsed.results[:20]:
            print(f"    {r.code} | {r.raw_item_name} = {r.raw_value} {r.unit} ref={r.reference_text}")
