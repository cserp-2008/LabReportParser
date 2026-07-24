import sys
import glob
sys.path.insert(0, 'D:/private/CS/CS/src/backend')

from parser.pdf_parser import PDFParser
from parser.jph_parser import JPHParser
from parser.nbmc_parser import NBMCParser

files = glob.glob("D:/private/CS/CS/src/storage/report/2026/07/*生化全套5*.pdf")
if files:
    file_path = files[0]
    print(f"=== 生化全套5.pdf ===")
    print(f"文件: {file_path}")
    
    pdf_parser = PDFParser()
    pages = pdf_parser.parse(file_path)
    
    if pages:
        coords_text = pages[0].ocr_coords_text
        lines = coords_text.split("\n")
        for line in lines:
            print(line)
        
        print(f"\n解析结果:")
        parser = JPHParser()
        report = parser.parse(coords_text)
        
        print(f"医院: {report.hospital_name}")
        print(f"采集时间: {report.sample_time}")
        print(f"报告时间: {report.report_time}")
        
        for r in report.results:
            item_name = getattr(r, 'item_name', '') or getattr(r, 'raw_item_name', '')
            raw_value = getattr(r, 'raw_value', '')
            unit = getattr(r, 'unit', '')
            ref = getattr(r, 'reference_text', '')
            print(f"    {item_name} = {raw_value} {unit} ref={ref}")
    else:
        print("无法解析PDF")

print("\n" + "="*60 + "\n")

files2 = glob.glob("D:/private/CS/CS/src/storage/report/2026/07/*血常规*.pdf")
if files2:
    file_path = files2[0]
    print(f"=== 血常规.pdf ===")
    print(f"文件: {file_path}")
    
    pdf_parser = PDFParser()
    pages = pdf_parser.parse(file_path)
    
    if pages:
        coords_text = pages[0].ocr_coords_text
        lines = coords_text.split("\n")
        for line in lines:
            print(line)
        
        print(f"\n省人医解析器:")
        parser = JPHParser()
        report = parser.parse(coords_text)
        print(f"医院: {report.hospital_name}")
        print(f"采集时间: {report.sample_time}")
        for r in report.results:
            item_name = getattr(r, 'item_name', '') or getattr(r, 'raw_item_name', '')
            raw_value = getattr(r, 'raw_value', '')
            unit = getattr(r, 'unit', '')
            ref = getattr(r, 'reference_text', '')
            print(f"    {item_name} = {raw_value} {unit} ref={ref}")
        
        print(f"\n明基医院解析器:")
        nbmc_parser = NBMCParser()
        nbmc_report = nbmc_parser.parse(coords_text)
        print(f"医院: {nbmc_report.hospital_name}")
        print(f"采集时间: {nbmc_report.sample_time}")
        for r in nbmc_report.results:
            item_name = getattr(r, 'item_name', '') or getattr(r, 'raw_item_name', '')
            raw_value = getattr(r, 'raw_value', '')
            unit = getattr(r, 'unit', '')
            ref = getattr(r, 'reference_text', '')
            print(f"    {item_name} = {raw_value} {unit} ref={ref}")
    else:
        print("无法解析PDF")
