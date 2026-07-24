"""检查生化全套报告解析情况"""
import sys
sys.path.insert(0, '.')

from db.session import SessionLocal
from db.models import Report, LabResult, Hospital

db = SessionLocal()

hospital = db.query(Hospital).filter(Hospital.hospital_name.like('%明基%')).first()

# 查找生化全套报告
reports = db.query(Report).filter(
    Report.hospital_id == hospital.hospital_id,
    Report.is_delete == 0,
    Report.file_name.like('%生化%')
).all()

print(f"生化全套报告数量: {len(reports)}")
for report in reports:
    result_count = db.query(LabResult).filter(LabResult.report_id == report.report_id).count()
    print(f"  {report.file_name} | 指标数={result_count} | 质量分={report.quality_score}")
    if result_count > 0:
        results = db.query(LabResult).filter(LabResult.report_id == report.report_id).all()
        for r in results[:10]:
            print(f"    {r.raw_item_name} = {r.raw_value} {r.unit} (ref={r.reference_text})")
        if len(results) > 10:
            print(f"    ... 共 {len(results)} 个指标")
    print()

db.close()
