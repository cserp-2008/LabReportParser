import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute('PRAGMA table_info(report)')
print('report表结构:')
for col in c.fetchall():
    print(f'  {col[1]} ({col[2]})')

c.execute("SELECT report_id, file_name, hospital_id, storage_path FROM report WHERE file_name LIKE '%2026-06-17EBV%' AND is_delete=0")
result = c.fetchone()
if result:
    print(f'\n报告信息:')
    print(f'  report_id: {result[0]}')
    print(f'  file_name: {result[1]}')
    print(f'  hospital_id: {result[2]}')
    print(f'  storage_path: {result[3]}')

conn.close()