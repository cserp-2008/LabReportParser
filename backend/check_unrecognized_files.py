import os
import sqlite3
from parser.pdf_parser import PDFParser

LABREPORT_DIR = r'D:\private\CS\CS\LabReport'

unrecognized_files = [
    '2026-05-06血型+不规则抗体.pdf',
    '2026-05-06血培养双侧双瓶（2需氧+2厌氧）.pdf',
    '2026-05-11一般细菌培养及鉴定(腹水)屎肠球菌.pdf'
]

for file_name in unrecognized_files:
    file_path = os.path.join(LABREPORT_DIR, file_name)
    print(f'\n=== {file_name} ===')
    print(f'文件存在: {os.path.exists(file_path)}')
    
    if os.path.exists(file_path):
        parser = PDFParser()
        pages = parser.parse(file_path)
        for i, page in enumerate(pages):
            print(f'\n--- 第{i+1}页 ---')
            print(page.text[:2000])
    else:
        print('文件不存在')