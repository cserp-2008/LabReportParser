import sqlite3
from parser.service import ParseService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Report

engine = create_engine('sqlite:///labreport.db')
Session = sessionmaker(bind=engine)
db = Session()

new_files = [
    '2026-05-06乙型肝炎DNA定量.pdf',
    '2026-05-06乙肝五项.pdf',
    '2026-05-06脂肪酶.pdf',
    '2026-05-06血型+不规则抗体.pdf',
    '2026-05-06血培养双侧双瓶（2需氧+2厌氧）.pdf',
    '2026-05-11一般细菌培养及鉴定(腹水)屎肠球菌.pdf'
]

print(f'开始重新解析 {len(new_files)} 个文件...\n')

for file_name in new_files:
    report = db.query(Report).filter(Report.file_name == file_name, Report.is_delete == 0).first()
    if not report:
        print(f'❌ 未找到报告: {file_name}')
        continue
    
    print(f'处理: {file_name}')
    print(f'  报告ID: {report.report_id}')
    print(f'  当前医院ID: {report.hospital_id}')
    
    report.hospital_id = 2
    
    service = ParseService(db)
    result = service.parse_report(report, parser_code='jph')
    
    result_count = result.get('result_count', 0)
    print(f'  识别指标: {result_count} 个')
    
    db.commit()
    print()

db.close()

print('重新解析完成！')