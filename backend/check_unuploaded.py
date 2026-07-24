import os
import sqlite3

LABREPORT_DIR = r'D:\private\CS\CS\LabReport'
DB_PATH = 'labreport.db'

all_files = []
for root, dirs, files in os.walk(LABREPORT_DIR):
    for file in files:
        if file.lower().endswith('.pdf'):
            full_path = os.path.join(root, file)
            all_files.append(file)

print(f'LabReport目录下共有 {len(all_files)} 个PDF文件')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT file_name FROM report WHERE is_delete=0")
uploaded_files = [row[0] for row in c.fetchall()]
conn.close()

print(f'数据库中已上传 {len(uploaded_files)} 个报告')

unuploaded = [f for f in all_files if f not in uploaded_files]
print(f'\n未上传的文件 ({len(unuploaded)} 个):')
for f in sorted(unuploaded):
    print(f'  {f}')

print(f'\n已上传但不在LabReport目录的文件 ({len([f for f in uploaded_files if f not in all_files])} 个):')
for f in sorted([f for f in uploaded_files if f not in all_files]):
    print(f'  {f}')