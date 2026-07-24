"""查看生化全套报告的表头和数据区域坐标"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser

pdf_dir = r'd:\private\CS\CS\src\labreptemplate\NBMC'
pdf_parser = PDFParser()

path = os.path.join(pdf_dir, '2026-01-07生化全套.pdf')
pages = pdf_parser.parse(path)

full_coords_text = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)
lines = full_coords_text.split("\n")

print('所有行（带坐标）:')
for line in lines:
    print(line)
