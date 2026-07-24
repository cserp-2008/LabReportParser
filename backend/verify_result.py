import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute('PRAGMA table_info(LabResult)')
print('LabResult表结构:')
for col in c.fetchall():
    print(f'  {col[1]} ({col[2]})')

report_id = '3c375595c08249b990f44362d2866c8c'

c.execute('''
    SELECT patient_name, gender, age, sample_time, report_time, hospital_id
    FROM report WHERE report_id = ?
''', (report_id,))
report = c.fetchone()
print(f'\n报告信息:')
print(f'  患者姓名: {report[0]}')
print(f'  性别: {report[1]}')
print(f'  年龄: {report[2]}')
print(f'  采样时间: {report[3]}')
print(f'  报告时间: {report[4]}')
print(f'  医院ID: {report[5]}')

c.execute('SELECT * FROM LabResult WHERE report_id = ?', (report_id,))
results = c.fetchall()
print(f'\n检验指标 ({len(results)} 个):')
for r in results:
    print(f'  {r[2]}: {r[4]} {r[5]} (参考: {r[6]})')

conn.close()