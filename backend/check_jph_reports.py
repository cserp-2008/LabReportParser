"""检查江苏省人民医院报告解析情况"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.session import SessionLocal
from db.models import Report, LabResult, Hospital
from parser.pdf_parser import PDFParser
from parser.jph_parser import JPHParser

db = SessionLocal()

hospitals = {h.hospital_id: h.hospital_name for h in db.query(Hospital).all()}

reports = db.query(Report).filter(
    Report.is_delete == 0,
    Report.file_name.like('%2026-05-08%')
).order_by(Report.file_name).all()

print(f"省人医5月8日报告共 {len(reports)} 份:\n")

pdf_parser = PDFParser()
jph_parser = JPHParser()

for report in reports:
    print(f"=== {report.file_name} ===")
    print(f"  质量分: {report.quality_score}")
    
    results = db.query(LabResult).filter(
        LabResult.report_id == report.report_id
    ).all()
    print(f"  解析指标数: {len(results)}")
    
    for r in results[:5]:
        item_code = getattr(r, 'item_code', None) or r.item_id
        item_name = getattr(r, 'item_name', None) or getattr(r, 'raw_item_name', '')
        raw_value = getattr(r, 'raw_value', '')
        print(f"    {item_code} | {item_name} = {raw_value} {r.unit} ref={r.reference_text}")
    if len(results) > 5:
        print(f"    ... 还有 {len(results) - 5} 项")
    
    if len(results) < 3:
        print(f"  [需要重新解析]")
        if os.path.exists(report.storage_path):
            pages = pdf_parser.parse(report.storage_path)
            if pages:
                full_coords_text = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)
                full_text = "\n".join(p.text for p in pages)
                
                print(f"  OCR使用: {any(p.ocr_used for p in pages)}")
                print(f"  坐标文本: {len(full_coords_text) > 0}")
                
                if full_coords_text:
                    parsed = jph_parser.parse(full_coords_text)
                else:
                    parsed = jph_parser.parse(full_text)
                
                print(f"  新解析指标数: {len(parsed.results)}")
                for r in parsed.results[:8]:
                    print(f"    {r.code} | {r.raw_item_name} = {r.raw_value} {r.unit} ref={r.reference_text}")
                if len(parsed.results) > 0:
                    for r in parsed.results[:15]:
                        print(f"    {r.code} | {r.raw_item_name} = {r.raw_value} {r.unit} ref={r.reference_text}")
                    if len(parsed.results) > 15:
                        print(f"    ... 还有 {len(parsed.results) - 15} 项")
    
    print()

db.close()
