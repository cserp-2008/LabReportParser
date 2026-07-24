import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute("SELECT report_id, hospital_id FROM report WHERE file_name LIKE '%2026-05-28血常规测定%' AND is_delete=0")
result = c.fetchone()
if result:
    report_id = result[0]
    print(f'报告ID: {report_id}')
    print(f'当前医院ID: {result[1]}')
else:
    print('未找到报告')
    conn.close()
    exit(1)

c.execute("SELECT hospital_id, hospital_name FROM Hospital WHERE hospital_name LIKE '%江苏省人民医院%'")
hospital = c.fetchone()
if hospital:
    jph_id = hospital[0]
    print(f'江苏省人民医院ID: {jph_id}')
else:
    print('未找到江苏省人民医院记录')
    conn.close()
    exit(1)

c.execute("UPDATE report SET hospital_id = ? WHERE report_id = ?", (jph_id, report_id))
conn.commit()
print(f'已将医院设置为江苏省人民医院')

conn.close()

from parser.service import ParseService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Report

engine = create_engine('sqlite:///labreport.db')
Session = sessionmaker(bind=engine)
db = Session()

report = db.query(Report).filter(Report.report_id == report_id).first()
if not report:
    print('报告不存在')
    db.close()
    exit(1)

print(f'\n文件名: {report.file_name}')
print(f'当前医院ID: {report.hospital_id}')

print('\n使用江苏省人民医院解析器(jph)重新解析...')
service = ParseService(db)
result = service.parse_report(report, parser_code='jph')

print(f'\n解析结果:')
print(f'  指标数: {result.get("result_count", 0)}')

db.commit()
db.close()

print('\n重新解析完成！')