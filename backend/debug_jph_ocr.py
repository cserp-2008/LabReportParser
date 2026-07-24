"""调试JPH解析器，查看OCR数据"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser

pdf_parser = PDFParser()

test_files = [
    r'd:\private\CS\CS\src\labreptemplate\JPH\2026-05-08乙肝5项等.pdf',
    r'd:\private\CS\CS\src\labreptemplate\JPH\2026-05-08血常规.pdf',
    r'd:\private\CS\CS\src\labreptemplate\JPH\2026-05-08肿瘤标志物.pdf',
]

for pdf_path in test_files:
    print(f"\n{'='*60}")
    print(f"文件: {os.path.basename(pdf_path)}")
    print('='*60)
    
    pages = pdf_parser.parse(pdf_path)
    if not pages:
        print('无法解析')
        continue
    
    for page in pages:
        print(f"\n--- 页面 {page.page_no} ---")
        print(f"分辨率: {page.width} x {page.height}")
        print(f"OCR使用: {page.ocr_used}")
        
        if page.ocr_coords_text:
            lines = page.ocr_coords_text.splitlines()
            print(f"OCR文本行数: {len(lines)}")
            
            print("\n前50行OCR数据:")
            for line in lines[:50]:
                print(line)
        else:
            print("\n文本内容:")
            for line in page.lines[:30]:
                print(line)