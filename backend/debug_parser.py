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
    
    print(f'  OCR坐标文本长度: {len(coords_text)}')
    
    ocr_items = nbmc_parser._parse_ocr_text(coords_text)
    print(f'  解析出OCR项目数: {len(ocr_items)}')
    
    if ocr_items:
        header_items = [i for i in ocr_items if nbmc_parser._is_header_text(i.text)]
        print(f'  表头项目数: {len(header_items)}')
        for h in header_items:
            print(f'    - ({h.x:.0f},{h.y:.0f}) {h.text}')
        
        layout = nbmc_parser._detect_layout(header_items, ocr_items)
        print(f'  检测到布局: {layout}')
        
        items = nbmc_parser._parse_table_from_coords(ocr_items)
        print(f'  解析出指标数: {len(items)}')
        
        for i, item in enumerate(items[:10], 1):
            print(f'    {i}. code={item.code}, name={item.name}, result={item.result}, unit={item.unit}, ref={item.ref_range}')
    
    print()
