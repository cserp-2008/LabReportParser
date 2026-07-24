import os

LABREPORT_DIR = r'D:\private\CS\CS\LabReport'

target_file = '2026-05-11一般细菌培养及鉴定(腹水)屎肠球菌.pdf'

for root, dirs, files in os.walk(LABREPORT_DIR):
    for file in files:
        if '一般细菌培养' in file:
            print(f'找到: {os.path.join(root, file)}')
            print(f'文件名: {file}')
            print()

import sqlite3
conn = sqlite3.connect('labreport.db')
c = conn.cursor()
c.execute("SELECT file_name FROM report WHERE file_name LIKE '%一般细菌培养%'")
results = c.fetchall()
print(f'数据库中类似文件名:')
for r in results:
    print(f'  {r[0]}')
conn.close()