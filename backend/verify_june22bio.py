import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

report_id = '5ea93d2fecab4d9d9b7da38cd08f9812'

c.execute('''
    SELECT patient_name, gender, age, sample_time, report_time, hospital_id
    FROM report WHERE report_id = ?
''', (report_id,))
report = c.fetchone()
print(f'报告信息:')
print(f'  患者姓名: {report[0]}')
print(f'  性别: {report[1]}')
print(f'  年龄: {report[2]}')
print(f'  采样时间: {report[3]}')
print(f'  报告时间: {report[4]}')

c.execute('SELECT * FROM Hospital WHERE hospital_id = ?', (report[5],))
hospital = c.fetchone()
print(f'  医院名称: {hospital[1]}')

c.execute('SELECT * FROM LabResult WHERE report_id = ?', (report_id,))
results = c.fetchall()
print(f'\n检验指标 ({len(results)} 个):')
for r in results:
    flag = f' {r[11]}' if r[11] else ''
    ref = f'{r[8]}-{r[9]}' if r[8] and r[9] else r[10]
    print(f'  {r[4]}: {r[5]} {r[7]} (参考: {ref}){flag}')

conn.close()