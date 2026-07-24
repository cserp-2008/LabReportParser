import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser
from parser.nbmc_parser import NBMCParser

pdf_dir = r'd:\private\CS\CS\src\labreptemplate\NBMC'
pdf_parser = PDFParser()
nbmc_parser = NBMCParser()

for fname in sorted(os.listdir(pdf_dir)):
    if not fname.endswith('.pdf'):
        continue
    
    if "甲状腺" not in fname:
        continue
    
    path = os.path.join(pdf_dir, fname)
    print(f'===== {fname} =====')
    
    pages = pdf_parser.parse(path)
    if not pages:
        print('  无法解析')
        continue
    
    coords_text = ""
    for p in pages:
        if p.ocr_coords_text:
            coords_text += p.ocr_coords_text + "\n"
    
    ocr_items = nbmc_parser._parse_ocr_text(coords_text)
    
    header_items = [i for i in ocr_items if nbmc_parser._is_header_text(i.text)]
    print(f'  表头项目:')
    for h in header_items:
        print(f'    - ({h.x:.0f},{h.y:.0f}) {h.text}')
    
    min_y = max(i.y for i in header_items) + 15
    footer_y = nbmc_parser._find_footer_y(ocr_items)
    
    print(f'  min_y: {min_y:.0f}, footer_y: {footer_y:.0f}')
    
    data_items = [i for i in ocr_items if min_y < i.y < footer_y and not nbmc_parser._is_header_text(i.text)]
    print(f'  数据项目数: {len(data_items)}')
    
    for d in data_items:
        print(f'    - ({d.x:.0f},{d.y:.0f}) {d.text}')
    
    rows = nbmc_parser._group_by_row(data_items)
    print(f'  行数: {len(rows)}')
    
    for r in rows:
        print(f'    行: {[(i.x, i.text) for i in r]}')
    
    print()
