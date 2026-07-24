"""检查坐标文本是否正确生成"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser

pdf_dir = r'd:\private\CS\CS\src\labreptemplate\NBMC'
pdf_parser = PDFParser()

for fname in sorted(os.listdir(pdf_dir)):
    if not fname.endswith('.pdf'):
        continue
    
    path = os.path.join(pdf_dir, fname)
    print(f'===== {fname} =====')
    
    pages = pdf_parser.parse(path)
    if not pages:
        print('  无法解析')
        continue
    
    print(f'  页数: {len(pages)}')
    for i, p in enumerate(pages):
        print(f'  Page {i+1}: text_lines={len(p.lines)}, ocr_coords_text={len(p.ocr_coords_text) if p.ocr_coords_text else 0} chars')
    
    full_coords_text = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)
    print(f'  合并后坐标文本: {len(full_coords_text)} chars')
    
    if full_coords_text:
        lines = full_coords_text.split("\n")
        print(f'  坐标行数: {len(lines)}')
        print('  前20行:')
        for line in lines[:20]:
            print(f'    {line[:100]}')
    
    print()
