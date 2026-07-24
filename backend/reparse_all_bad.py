import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import LabResult, Report, Hospital
from parser.service import ParseService

engine = create_engine('sqlite:///labreport.db')
Session = sessionmaker(bind=engine)
db = Session()

bad_keywords = ['采集时间', '样本号', '地址：', '检测结果可能受', 'cid:']

def has_bad_items(report_id: str) -> bool:
    items = db.query(LabResult.raw_item_name).filter(LabResult.report_id == report_id).all()
    for item in items:
        name = item[0] or ""
        for keyword in bad_keywords:
            if keyword in name:
                return True
    return False

bad_reports = []
reports = db.query(Report).filter(Report.is_delete == 0).all()

for report in reports:
    if has_bad_items(report.report_id):
        bad_reports.append(report)

print(f"找到 {len(bad_reports)} 个包含非化验指标的报告")

service = ParseService(db)
success_count = 0
fail_count = 0

for idx, report in enumerate(bad_reports, 1):
    print(f"\n[{idx}/{len(bad_reports)}] 重新解析: {report.file_name}")
    
    try:
        old_count = db.query(LabResult).filter(LabResult.report_id == report.report_id).count()
        
        hospital = db.query(Hospital).filter(Hospital.hospital_id == report.hospital_id).first()
        parser_code = hospital.parser_code.lower() if hospital else None
        
        result = service.parse_report(report, parser_code=parser_code)
        
        new_count = db.query(LabResult).filter(LabResult.report_id == report.report_id).count()
        
        if has_bad_items(report.report_id):
            print(f"  ⚠️  仍然包含非化验指标")
            fail_count += 1
        else:
            print(f"  ✓ 成功！旧记录: {old_count}, 新记录: {new_count}")
            success_count += 1
            
        db.commit()
    except Exception as e:
        print(f"  ✗ 失败: {str(e)}")
        fail_count += 1
        db.rollback()

db.close()

print(f"\n=== 完成 ===")
print(f"成功: {success_count}")
print(f"失败: {fail_count}")
