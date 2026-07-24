"""查看生化全套报告中有问题的行的详细坐标"""
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
ocr_items = nbmc_parser._parse_ocr_text(full_coords_text)

header_items = [i for i in ocr_items if nbmc_parser._is_header_text(i.text)]
min_y = max(i.y for i in header_items) + 15
footer_y = nbmc_parser._find_footer_y(ocr_items)

data_items = [i for i in ocr_items if min_y < i.y < footer_y and not nbmc_parser._is_header_text(i.text)]
rows = nbmc_parser._group_by_row(data_items)

print(f'总行数: {len(rows)}')
print('\n所有数据行:')
for idx, row in enumerate(rows):
    row_str = " | ".join(f'({i.x:.0f},{i.y:.0f}){i.text}' for i in row)
    print(f'  Row {idx+1}: {row_str}')
