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
    coords_text = ""
    for p in pages:
        if p.ocr_coords_text:
            coords_text += p.ocr_coords_text + "\n"
    
    ocr_items = nbmc_parser._parse_ocr_text(coords_text)
    header_items = [i for i in ocr_items if nbmc_parser._is_header_text(i.text)]
    
    min_y = max(i.y for i in header_items) + 15
    footer_y = nbmc_parser._find_footer_y(ocr_items)
    
    data_items = [i for i in ocr_items if min_y < i.y < footer_y and not nbmc_parser._is_header_text(i.text)]
    rows = nbmc_parser._group_by_row(data_items)
    
    print(f'  布局检测: {nbmc_parser._detect_layout(header_items, ocr_items)}')
    
    for row in rows:
        print(f'    行数据:')
        for i in row:
            print(f'      ({i.x:.0f},{i.y:.0f}) "{i.text}"')
        
        item = nbmc_parser.NBMCItem(code="", name="", result="", unit="", ref_range="")
        for i in row:
            if i.x < 300:
                if nbmc_parser._is_valid_code(i.text):
                    item.code = i.text
                else:
                    item.name += i.text
            elif i.x < 650:
                item.name += i.text
            elif i.x < 850:
                item.result += i.text
            elif i.x < 950:
                pass
            elif i.x < 1150:
                item.unit += i.text
            else:
                item.ref_range += i.text
        
        print(f'    解析结果: code={item.code}, name={item.name}, result={item.result}, unit={item.unit}, ref={item.ref_range}')
        print(f'    有效结果: {item.name and item.result and nbmc_parser._is_valid_result(item.result)}')
    
    print()
