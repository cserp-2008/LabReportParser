import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser
from parser.jph_parser import JPHParser
from parser.hospital_detector import HospitalDetector

file_path = r'D:\private\CS\CS\LabReport\2026-01-07甲状腺激素.pdf'

print(f"测试文件: {file_path}")
print("=" * 80)

pdf_parser = PDFParser()
pages = pdf_parser.parse(file_path)

for page in pages:
    print(f"\n--- 第 {page.page_no} 页 ---")
    print(f"文本内容（前500字符）:")
    print(page.text[:500])
    print("\nOCR坐标文本（前10行）:")
    lines = page.ocr_coords_text.split("\n")[:10]
    for line in lines:
        print(line)

print("\n" + "=" * 80)
print("医院识别结果:")
detector = HospitalDetector()
hospital = detector.detect("\n".join(p.text for p in pages))
print(f"识别出的医院: {hospital}")

print("\n" + "=" * 80)
print("JPH解析器测试:")
jph_parser = JPHParser()
full_coords_text = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)
if full_coords_text:
    parsed = jph_parser.parse(full_coords_text)
    print(f"患者姓名: {parsed.patient_name}")
    print(f"采样时间: {parsed.sample_time}")
    print(f"指标数量: {len(parsed.results)}")
    for r in parsed.results[:5]:
        print(f"  - {r.raw_item_name}: {r.raw_value} {r.unit or ''}")
else:
    print("没有OCR坐标文本，使用普通文本解析")
    parsed = jph_parser.parse("\n".join(p.text for p in pages))
    print(f"指标数量: {len(parsed.results)}")
