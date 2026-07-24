import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print('数据库表列表:')
for table in tables:
    print(f'  {table[0]}')

c.execute("SELECT report_id, file_name, hospital_id FROM report WHERE file_name LIKE ?", ('%屎肠球菌%',))
results = c.fetchall()
print('\n屎肠球菌相关报告:')
for r in results:
    print(f'  {r}')

c.execute("SELECT COUNT(*) FROM LabResult WHERE report_id=?", ('57a794f12a0d4dbaa341c944aa909fde',))
result_count = c.fetchone()[0]
print(f'\n新上传报告指标数量: {result_count}')

conn.close()
