import sqlite3
from parser.service import ParseService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Report

engine = create_engine('sqlite:///labreport.db')
Session = sessionmaker(bind=engine)
db = Session()

files_to_reparse = [
    ('2026-05-06血型+不规则抗体.pdf', 3, 'nsh'),
    ('2026-05-06血培养双侧双瓶（2需氧+2厌氧）.pdf', 3, 'nsh'),
]

print('开始用正确的医院解析器重新解析...\n')

for file_name, hospital_id, parser_code in files_to_reparse:
    report = db.query(Report).filter(Report.file_name == file_name, Report.is_delete == 0).first()
    if not report:
        print(f'❌ 未找到报告: {file_name}')
        continue
    
    print(f'处理: {file_name}')
    
    c = db.connection().connection.cursor()
    c.execute('SELECT hospital_name FROM Hospital WHERE hospital_id = ?', (hospital_id,))
    hospital_name = c.fetchone()[0]
    print(f'  医院: {hospital_name}')
    
    report.hospital_id = hospital_id
    
    service = ParseService(db)
    result = service.parse_report(report, parser_code=parser_code)
    
    result_count = result.get('result_count', 0)
    print(f'  识别指标: {result_count} 个')
    
    db.commit()
    print()

db.close()

print('重新解析完成！')