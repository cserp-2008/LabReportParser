import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute("SELECT report_id, hospital_id, file_name FROM report WHERE file_name LIKE '%2026-06-22血常规测定%' AND is_delete=0")
result = c.fetchone()
if result:
    print(f'report_id: {result[0]}')
    print(f'hospital_id: {result[1]}')
    print(f'file_name: {result[2]}')
else:
    print('未找到报告')

conn.close()