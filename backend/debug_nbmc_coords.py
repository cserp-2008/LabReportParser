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
    
    print(f'  页面数: {len(pages)}')
    print(f'  使用OCR: {pages[0].ocr_used}')
    print(f'  页面宽度: {pages[0].width}, 高度: {pages[0].height}')
    print()
    
    print('  OCR坐标数据（前50行）:')
    coords_lines = pages[0].ocr_coords_text.split('\n')
    for i, line in enumerate(coords_lines[:50], 1):
        print(f'    {i}. {line}')
    
    if len(coords_lines) > 50:
        print(f'    ... 还有 {len(coords_lines) - 50} 行')
    
    print()
    
    print('  重组后的文本行（前30行）:')
    text_lines = pages[0].text.split('\n')
    for i, line in enumerate(text_lines[:30], 1):
        print(f'    {i}. {line}')
    
    if len(text_lines) > 30:
        print(f'    ... 还有 {len(text_lines) - 30} 行')
    
    print()
