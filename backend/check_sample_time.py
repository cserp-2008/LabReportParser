import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM Report WHERE sample_time IS NULL")
result = c.fetchone()
print("sample_time为空的报告数:", result[0])

c.execute("SELECT COUNT(*) FROM Report")
result = c.fetchone()
print("报告总数:", result[0])

c.execute("""
    SELECT r.sample_time, lr.raw_value, lr.value_numeric, r.file_name 
    FROM LabResult lr 
    JOIN Report r ON lr.report_id = r.report_id 
    WHERE lr.item_id = 37
    ORDER BY r.sample_time
""")
results = c.fetchall()
print("\n谷丙转氨酶所有记录(按sample_time排序):")
for r in results:
    print(f"时间: {r[0]}, 值: {r[1]}, 数值: {r[2]}, 文件名: {r[3][:30]}...")

conn.close()
