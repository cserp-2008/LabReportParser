"""调试省人生化全套OCR数据"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser
from parser.jph_parser import JPHParser

pdf_parser = PDFParser()
jph_parser = JPHParser()

file_path = "D:\\private\\CS\\CS\\src\\storage\\report\\2026\\07\\f85b5407890f4611a801b0358a60b195_2026-05-08生化全套18.pdf"

if os.path.exists(file_path):
    pages = pdf_parser.parse(file_path)
    if pages:
        full_coords_text = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)
        print("=== OCR坐标数据 ===")
        lines = full_coords_text.split("\n")
        for i, line in enumerate(lines[:80]):
            print(f"{i}: {line}")
        
        parsed = jph_parser.parse(full_coords_text)
        print(f"\n=== 解析结果 ===")
        for r in parsed.results[:10]:
            print(f"    {r.code} | {r.raw_item_name} = {r.raw_value} {r.unit} ref={r.reference_text}")
else:
    print(f"文件不存在: {file_path}")
