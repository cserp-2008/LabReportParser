"""重新扫描存储目录并导入所有报告（修复版）"""
import sys
sys.path.insert(0, '.')
import os
import re
import shutil

from db.session import SessionLocal
from db.models import Report, Hospital
from parser.service import ParseService
from utils.file_utils import generate_report_id, generate_task_id, calculate_md5, get_storage_path
from core.config import config

db = SessionLocal()

hospital = db.query(Hospital).filter(Hospital.hospital_name.like('%明基%')).first()
if not hospital:
    print("未找到明基医院")
    exit()

template_dir = r'd:\private\CS\CS\src\labreptemplate\NBMC'
storage_root = config['storage_root']
service = ParseService(db)

count = 0
success_count = 0
fail_count = 0

for fname in sorted(os.listdir(template_dir)):
    if not fname.endswith('.pdf'):
        continue
    
    source_path = os.path.join(template_dir, fname)
    file_size = os.path.getsize(source_path)
    file_md5 = calculate_md5(source_path)
    
    existing = db.query(Report).filter(Report.file_md5 == file_md5).first()
    if existing:
        print(f"跳过（已存在）: {fname}")
        continue
    
    report_id = generate_report_id()
    task_id = generate_task_id()
    
    storage_path = get_storage_path(storage_root, report_id, fname)
    os.makedirs(os.path.dirname(storage_path), exist_ok=True)
    shutil.copy2(source_path, storage_path)
    
    report = Report(
        report_id=report_id,
        task_id=task_id,
        file_name=fname,
        file_type='pdf',
        file_size=file_size,
        file_md5=file_md5,
        storage_path=storage_path,
        page_count=1,
        quality_score=0,
        review_status=0,
        hospital_id=hospital.hospital_id
    )
    db.add(report)
    db.commit()
    
    print(f"解析: {fname}")
    try:
        result = service.parse_report(report)
        success_count += 1
        print(f"  成功: 指标数={result.get('result_count', 0)}, 质量分={result.get('quality_score', 0):.1f}")
    except Exception as e:
        fail_count += 1
        print(f"  失败: {e}")
    
    count += 1

db.commit()
db.close()

print(f"\n完成！共处理 {count} 个文件，成功 {success_count} 个，失败 {fail_count} 个")