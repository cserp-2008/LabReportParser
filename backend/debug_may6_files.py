"""调试5月6日报告解析问题"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser
from parser.nsh_parser import NSHParser
from parser.nbmc_parser import NBMCParser
from parser.jph_parser import JPHParser
from parser.hospital_detector import HospitalDetector

def main():
    test_dir = r"D:\private\CS\CS\src\storage\report\2026\07"
    if not os.path.exists(test_dir):
        print(f"目录不存在: {test_dir}")
        return
    
    pdf_files = sorted(glob.glob(os.path.join(test_dir, "*05-06*.pdf")))
    
    if not pdf_files:
        print("未找到5月6日的PDF文件")
        return
    
    pdf_parser = PDFParser()
    hospital_detector = HospitalDetector()
    
    for pdf_file in pdf_files:
        print("=" * 80)
        print(f"文件: {os.path.basename(pdf_file)}")
        
        try:
            pages = pdf_parser.parse(pdf_file)
            full_text = "\n".join(p.text for p in pages)
            full_coords_text = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)
            
            hospital_name = hospital_detector.detect(full_text)
            print(f"  医院识别: {hospital_name}")
            
            if "南京市第二医院" in (hospital_name or ""):
                parser = NSHParser()
                parser_name = "市二院解析器"
                use_coords = True
            elif "明基" in (hospital_name or ""):
                parser = NBMCParser()
                parser_name = "明基医院解析器"
                use_coords = True
            elif "江苏省人民医院" in (hospital_name or ""):
                parser = JPHParser()
                parser_name = "省人医解析器"
                use_coords = True
            else:
                parser = JPHParser()
                parser_name = "省人医解析器"
                use_coords = False
            
            print(f"  使用解析器: {parser_name}")
            print(f"  使用坐标数据: {use_coords}")
            
            if use_coords and full_coords_text:
                if parser_name == "市二院解析器":
                    report = parser.parse(full_text, 1, full_coords_text)
                else:
                    report = parser.parse(full_coords_text)
            else:
                report = parser.parse(full_text)
            
            print(f"  采集时间: {report.sample_time}")
            print(f"  报告时间: {report.report_time}")
            print(f"  解析指标数: {len(report.results)}")
            
            if len(report.results) > 0:
                for i, item in enumerate(report.results[:5]):
                    code = getattr(item, 'code', '')
                    print(f"    {code} {item.raw_item_name} = {item.raw_value} {item.unit} ref={item.reference_text}")
                
                if len(report.results) > 5:
                    print(f"    ... 还有 {len(report.results) - 5} 项指标")
            else:
                print("  未解析到任何指标")
                print(f"  文本前500字符:")
                print(f"  {full_text[:500]}")
            
        except Exception as e:
            print(f"  解析错误: {e}")
    
    print(f"\n共测试 {len(pdf_files)} 个5月6日的报告文件")

if __name__ == "__main__":
    main()