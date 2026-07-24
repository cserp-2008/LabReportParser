import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser
from parser.jph_parser import JPHParser

file_path = r"D:\private\CS\CS\src\storage\report\2026\07\25e7cba9896947669fe8939ccbd84969_2026-05-08生化全套5.pdf"

if os.path.exists(file_path):
    print(f"文件存在: {file_path}")
    
    pdf_parser = PDFParser()
    jph_parser = JPHParser()
    
    pages = pdf_parser.parse(file_path)
    
    if pages:
        full_coords_text = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)
        print(f"\n=== OCR坐标数据（前100行）===")
        lines = full_coords_text.split("\n")[:100]
        for i, line in enumerate(lines):
            print(f"{i}: {line}")
        
        parsed = jph_parser.parse(full_coords_text)
        print(f"\n=== 解析结果 ===")
        for r in parsed.results:
            print(f"    {r.code} | {r.raw_item_name} = {r.raw_value} {r.unit} ref={r.reference_text}")
    else:
        print("PDF解析失败")
else:
    print(f"文件不存在: {file_path}")