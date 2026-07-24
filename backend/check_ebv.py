import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute("SELECT report_id, hospital_id, file_name FROM report WHERE file_name LIKE '%2026-06-17EBV%' AND is_delete=0")
result = c.fetchone()
if result:
    report_id = result[0]
    print(f'报告ID: {report_id}')
    print(f'当前医院ID: {result[1]}')
    print(f'文件名: {result[2]}')
else:
    print('未找到报告')
    conn.close()
    exit(1)

c.execute('SELECT * FROM LabResult WHERE report_id = ?', (report_id,))
results = c.fetchall()
print(f'\n当前识别指标数: {len(results)}')
if results:
    print('指标列表:')
    for r in results:
        flag = f' {r[11]}' if r[11] else ''
        print(f'  {r[4]}: {r[5]} {r[7]} {flag}')

conn.close()