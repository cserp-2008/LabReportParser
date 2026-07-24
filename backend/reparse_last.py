import sqlite3
from parser.service import ParseService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Report

engine = create_engine('sqlite:///labreport.db')
Session = sessionmaker(bind=engine)
db = Session()

file_name = '2026-05-11一般细菌培养及鉴定(腹水)屎肠球菌.pdf'

report = db.query(Report).filter(Report.file_name == file_name, Report.is_delete == 0).first()
if not report:
    print('未找到报告')
    db.close()
    exit(1)

print(f'报告ID: {report.report_id}')
print(f'当前医院ID: {report.hospital_id}')

report.hospital_id = 2

service = ParseService(db)
result = service.parse_report(report, parser_code='jph')

result_count = result.get('result_count', 0)
print(f'识别指标: {result_count} 个')

db.commit()
db.close()

print('\n重新解析完成！')