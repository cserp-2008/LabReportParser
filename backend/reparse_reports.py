import sqlite3
import sys

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute('''
    SELECT r.report_id, r.file_name, r.hospital_id, COUNT(lr.result_id) as cnt
    FROM report r
    LEFT JOIN LabResult lr ON r.report_id = lr.report_id
    WHERE r.is_delete=0
    GROUP BY r.report_id
    HAVING cnt = 0
''')
zero_reports = c.fetchall()

conn.close()

print(f"零指标报告数: {len(zero_reports)}")

if not zero_reports:
    print("没有零指标报告，无需重新解析")
    sys.exit(0)

from parser.service import ParseService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Report

engine = create_engine('sqlite:///labreport.db')
Session = sessionmaker(bind=engine)
db = Session()

success_count = 0
fail_count = 0
no_hospital_count = 0

parsers_to_try = ['common', 'jph', 'nbmc', 'nsh']

for r in zero_reports:
    report_id = r[0]
    file_name = r[1]
    hospital_id = r[2]
    
    print(f"\n处理: {file_name}")
    
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        print(f"  ❌ 报告不存在")
        fail_count += 1
        continue
    
    if hospital_id is None:
        print(f"  ⚠️ 医院未识别，尝试使用不同解析器...")
        no_hospital_count += 1
        
        success = False
        for parser_code in parsers_to_try:
            try:
                service = ParseService(db)
                result = service.parse_report(report, parser_code=parser_code)
                if result.get('result_count', 0) > 0:
                    print(f"  ✅ 使用 {parser_code} 解析成功: {result['result_count']} 个指标")
                    success_count += 1
                    success = True
                    break
            except Exception as e:
                print(f"  ⚠️ 使用 {parser_code} 解析异常: {str(e)[:30]}")
        
        if not success:
            print(f"  ❌ 所有解析器均失败")
            fail_count += 1
    else:
        try:
            service = ParseService(db)
            result = service.parse_report(report)
            if result.get('result_count', 0) > 0:
                print(f"  ✅ 重新解析成功: {result['result_count']} 个指标")
                success_count += 1
            else:
                print(f"  ❌ 重新解析仍无指标")
                fail_count += 1
        except Exception as e:
            print(f"  ❌ 重新解析异常: {str(e)[:30]}")
            fail_count += 1

db.commit()
db.close()

print(f"\n{'='*50}")
print(f"重新解析完成:")
print(f"  医院未识别报告数: {no_hospital_count}")
print(f"  成功: {success_count}")
print(f"  失败: {fail_count}")