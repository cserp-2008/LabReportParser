import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute('SELECT COUNT(*) FROM report WHERE is_delete=0')
total = c.fetchone()[0]
print(f"报告总数: {total}")

c.execute('SELECT COUNT(*) FROM report WHERE is_delete=0 AND hospital_id IS NULL')
no_hospital = c.fetchone()[0]
print(f"医院未识别: {no_hospital}")

c.execute('SELECT COUNT(*) FROM LabResult')
total_results = c.fetchone()[0]
print(f"检验指标总数: {total_results}")

c.execute('''
    SELECT COUNT(DISTINCT report_id) FROM LabResult
''')
reports_with_results = c.fetchone()[0]
print(f"有指标的报告数: {reports_with_results}")
print(f"零指标报告数: {total - reports_with_results}")

c.execute('''
    SELECT r.report_id, r.file_name, r.hospital_id, COUNT(lr.result_id) as cnt
    FROM report r
    LEFT JOIN LabResult lr ON r.report_id = lr.report_id
    WHERE r.is_delete=0
    GROUP BY r.report_id
    HAVING cnt = 0
''')
zero_reports = c.fetchall()

if zero_reports:
    print("\n零指标报告列表:")
    for r in zero_reports:
        hospital_str = "(医院未识别)" if not r[2] else f"(医院ID: {r[2]})"
        print(f"  {r[0]} - {r[1]} {hospital_str}")

conn.close()