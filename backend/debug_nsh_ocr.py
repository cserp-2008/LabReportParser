"""查看市二院报告的OCR坐标数据"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser

def main():
    test_file = r"D:\private\CS\CS\src\storage\report\2026\07\8877f7bb2fba402a985d2b15f77641af_2026-05-06尿液分析.pdf"
    
    if not os.path.exists(test_file):
        print(f"文件不存在: {test_file}")
        return
    
    pdf_parser = PDFParser()
    pages = pdf_parser.parse(test_file)
    
    print("=" * 80)
    print("坐标文本:")
    print("=" * 80)
    for page in pages:
        print(page.ocr_coords_text)

if __name__ == "__main__":
    main()