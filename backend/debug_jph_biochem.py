"""调试生化全套双栏布局"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser

pdf_parser = PDFParser()

pdf_path = r'd:\private\CS\CS\src\labreptemplate\JPH\2026-05-09生化全套I.pdf'
print(f"文件: {os.path.basename(pdf_path)}")

pages = pdf_parser.parse(pdf_path)
if pages:
    page = pages[0]
    print(f"\n页面尺寸: {page.width} x {page.height}")
    print(f"OCR文本行数: {len(page.ocr_coords_text.splitlines())}")
    
    print("\n所有OCR数据:")
    for line in page.ocr_coords_text.splitlines():
        print(line)