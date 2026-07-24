import sys
import glob
sys.path.insert(0, 'D:/private/CS/CS/src/backend')

from parser.pdf_parser import PDFParser
from parser.jph_parser import JPHParser

files = glob.glob("D:/private/CS/CS/src/storage/report/2026/07/*血氨*.pdf")
if files:
    file_path = files[0]
    print(f"=== 血氨测定报告 ===")
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
        
        ocr_items = parser._parse_ocr_text(coords_text)
        header_items = [i for i in ocr_items if parser._is_header_text(i["text"])]
        boundaries = parser._detect_column_boundaries(header_items)
        print(f"边界检测结果:")
        print(f"  code={boundaries['code']}, name={boundaries['name']}")
        print(f"  result={boundaries['result']}, unit={boundaries['unit']}")
        print(f"  ref_range={boundaries['ref_range']}")
        
        report = parser.parse(coords_text)
        
        for r in report.results:
            item_name = getattr(r, 'item_name', '') or getattr(r, 'raw_item_name', '')
            raw_value = getattr(r, 'raw_value', '')
            unit = getattr(r, 'unit', '')
            ref = getattr(r, 'reference_text', '')
            print(f"    {item_name} = {raw_value} {unit} ref={ref}")
    else:
        print("无法解析PDF")

print("\n" + "="*60 + "\n")

files2 = glob.glob("D:/private/CS/CS/src/storage/report/2026/07/*心肌标志物*.pdf")
if files2:
    file_path = files2[0]
    print(f"=== 心肌标志物报告 ===")
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
        
        ocr_items = parser._parse_ocr_text(coords_text)
        header_items = [i for i in ocr_items if parser._is_header_text(i["text"])]
        boundaries = parser._detect_column_boundaries(header_items)
        print(f"边界检测结果:")
        print(f"  code={boundaries['code']}, name={boundaries['name']}")
        print(f"  result={boundaries['result']}, unit={boundaries['unit']}")
        print(f"  ref_range={boundaries['ref_range']}")
        
        report = parser.parse(coords_text)
        
        for r in report.results:
            item_name = getattr(r, 'item_name', '') or getattr(r, 'raw_item_name', '')
            raw_value = getattr(r, 'raw_value', '')
            unit = getattr(r, 'unit', '')
            ref = getattr(r, 'reference_text', '')
            print(f"    {item_name} = {raw_value} {unit} ref={ref}")
    else:
        print("无法解析PDF")
