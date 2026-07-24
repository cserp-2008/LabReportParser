"""调试2026-01-07生化全套报告"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser
from parser.hospital_detector import HospitalDetector

def main():
    test_file = r"D:\private\CS\CS\src\storage\report\2026\07\0a7c4f35590d44159b6ef4413248f5b0_2026-01-07生化全套.pdf"
    
    if not os.path.exists(test_file):
        print(f"文件不存在: {test_file}")
        return
    
    pdf_parser = PDFParser()
    pages = pdf_parser.parse(test_file)
    
    print("=" * 80)
    print("纯文本内容:")
    print("=" * 80)
    for i, page in enumerate(pages):
        print(f"--- 第{i+1}页 ---")
        for j, line in enumerate(page.text.split("\n")):
            if line.strip():
                print(f"  {j:3d}: {repr(line)}")
    
    print("\n" + "=" * 80)
    print("医院识别:")
    print("=" * 80)
    full_text = "\n".join(p.text for p in pages)
    detector = HospitalDetector()
    hospital = detector.detect(full_text)
    print(f"识别结果: {hospital}")
    
    print("\n" + "=" * 80)
    print("坐标文本（前3000字符）:")
    print("=" * 80)
    full_coords = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)
    print(full_coords[:3000])

if __name__ == "__main__":
    main()