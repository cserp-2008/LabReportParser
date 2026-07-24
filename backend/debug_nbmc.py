"""调试NBMC解析器"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser
from parser.nbmc_parser import NBMCParser

pdf_dir = r'd:\private\CS\CS\src\labreptemplate\NBMC'
pdf_parser = PDFParser()
nbmc_parser = NBMCParser()

path = os.path.join(pdf_dir, '2026-01-07生化全套.pdf')
pages = pdf_parser.parse(path)

full_coords_text = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)
print(f'坐标文本行数: {len(full_coords_text.split("\n"))}')

ocr_items = nbmc_parser._parse_ocr_text(full_coords_text)
print(f'OCR items数: {len(ocr_items)}')

header_items = [i for i in ocr_items if nbmc_parser._is_header_text(i.text)]
print(f'表头items数: {len(header_items)}')
for h in header_items:
    print(f'  ({h.x:.0f},{h.y:.0f}) {h.text}')

layout = nbmc_parser._detect_layout(header_items)
print(f'检测到布局: {layout}')

if header_items:
    min_y = max(i.y for i in header_items) + 15
    footer_y = nbmc_parser._find_footer_y(ocr_items)
    print(f'min_y={min_y:.0f}, footer_y={footer_y:.0f}')
    
    data_items = [i for i in ocr_items if min_y < i.y < footer_y and not nbmc_parser._is_header_text(i.text)]
    print(f'数据items数: {len(data_items)}')
    
    rows = nbmc_parser._group_by_row(data_items)
    print(f'行数: {len(rows)}')
    
    print('\n前5行数据:')
    for idx, row in enumerate(rows[:5]):
        row_str = " | ".join(f'({i.x:.0f},{i.y:.0f}){i.text}' for i in row)
        print(f'  Row {idx+1}: {row_str}')
