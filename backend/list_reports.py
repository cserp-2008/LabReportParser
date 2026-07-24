"""查看所有明基医院报告"""
import sys
sys.path.insert(0, '.')

from db.session import SessionLocal
from db.models import Report, LabResult, Hospital

db = SessionLocal()

hospital = db.query(Hospital).filter(Hospital.hospital_name.like('%明基%')).first()

reports = db.query(Report).filter(
    Report.hospital_id == hospital.hospital_id,
    Report.is_delete == 0
).all()

print(f"明基医院报告总数: {len(reports)}")
for report in reports:
    result_count = db.query(LabResult).filter(LabResult.report_id == report.report_id).count()
    print(f"  {report.file_name} | 指标数={result_count} | 质量分={report.quality_score}")

db.close()
