"""测试原有解析器解析2026-01-07生化全套报告"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser
from parser.hospital_detector import HospitalDetector
from parser.jph_parser import JPHParser
from parser.nbmc_parser import NBMCParser
from parser.nsh_parser import NSHParser

def main():
    test_file = r"D:\private\CS\CS\src\storage\report\2026\07\0a7c4f35590d44159b6ef4413248f5b0_2026-01-07生化全套.pdf"
    
    if not os.path.exists(test_file):
        print(f"文件不存在: {test_file}")
        return
    
    pdf_parser = PDFParser()
    pages = pdf_parser.parse(test_file)
    
    full_text = "\n".join(p.text for p in pages)
    full_coords_text = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)
    
    detector = HospitalDetector()
    hospital_name = detector.detect(full_text)
    print(f"医院识别: {hospital_name}")
    
    if "明基" in (hospital_name or ""):
        parser = NBMCParser()
        parser_name = "明基医院解析器"
        use_coords = True
    elif "江苏省人民医院" in (hospital_name or ""):
        parser = JPHParser()
        parser_name = "省人医解析器"
        use_coords = True
    elif "南京市第二医院" in (hospital_name or ""):
        parser = NSHParser()
        parser_name = "市二院解析器"
        use_coords = True
    else:
        parser = JPHParser()
        parser_name = "省人医解析器"
        use_coords = False
    
    print(f"使用解析器: {parser_name}")
    print(f"使用坐标数据: {use_coords}")
    
    if use_coords and full_coords_text:
        report = parser.parse(full_coords_text)
    else:
        report = parser.parse(full_text)
    
    print(f"采集时间: {report.sample_time}")
    print(f"报告时间: {report.report_time}")
    print(f"患者姓名: {report.patient_name}")
    print(f"解析指标数: {len(report.results)}")
    
    if len(report.results) > 0:
        print("\n解析结果:")
        for i, item in enumerate(report.results):
            code = getattr(item, 'code', '')
            print(f"  {code} {item.raw_item_name} = {item.raw_value} {item.unit} ref={item.reference_text}")
    else:
        print("未解析到任何指标")

if __name__ == "__main__":
    main()