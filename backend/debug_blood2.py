import sys
import glob
sys.path.insert(0, 'D:/private/CS/CS/src/backend')

from parser.pdf_parser import PDFParser
from parser.jph_parser import JPHParser
from parser.nbmc_parser import NBMCParser

files = glob.glob("D:/private/CS/CS/src/storage/report/2026/07/*血常规*.pdf")
if files:
    file_path = files[0]
    print(f"找到文件: {file_path}")
    
    pdf_parser = PDFParser()
    pages = pdf_parser.parse(file_path)
    
    if pages:
        coords_text = pages[0].ocr_coords_text
        print(f"\n坐标文本长度: {len(coords_text)}")
        
        print(f"\n=== OCR坐标数据（全部）===")
        lines = coords_text.split("\n")
        for i, line in enumerate(lines):
            print(f"{i}: {line}")
        
        print(f"\n=== 省人医解析器结果 ===")
        parser = JPHParser()
        report = parser.parse(coords_text)
        
        for r in report.results:
            item_code = getattr(r, 'item_code', None) or getattr(r, 'item_id', '')
            item_name = getattr(r, 'item_name', '') or getattr(r, 'raw_item_name', '')
            raw_value = getattr(r, 'raw_value', '')
            unit = getattr(r, 'unit', '')
            ref = getattr(r, 'reference_text', '')
            print(f"    {item_code} | {item_name} = {raw_value} {unit} ref={ref}")
        
        print(f"\n=== 明基医院解析器结果 ===")
        nbmc_parser = NBMCParser()
        nbmc_report = nbmc_parser.parse(coords_text)
        
        for r in nbmc_report.results:
            item_code = getattr(r, 'item_code', None) or getattr(r, 'item_id', '')
            item_name = getattr(r, 'item_name', '') or getattr(r, 'raw_item_name', '')
            raw_value = getattr(r, 'raw_value', '')
            unit = getattr(r, 'unit', '')
            ref = getattr(r, 'reference_text', '')
            print(f"    {item_code} | {item_name} = {raw_value} {unit} ref={ref}")
    else:
        print("无法解析PDF")
else:
    print("未找到文件")
