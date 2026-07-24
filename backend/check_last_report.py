import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute("SELECT report_id, file_name, hospital_id, is_delete FROM report WHERE file_name LIKE '%一般细菌培养%腹水%屎肠球菌%'")
results = c.fetchall()
print(f'找到 {len(results)} 条记录:')
for r in results:
    print(f'  report_id: {r[0]}')
    print(f'  file_name: {r[1]}')
    print(f'  hospital_id: {r[2]}')
    print(f'  is_delete: {r[3]}')
    print()

c.execute("SELECT COUNT(*) FROM report WHERE is_delete=0")
total = c.fetchone()[0]
print(f'\n数据库中报告总数: {total}')

conn.close()