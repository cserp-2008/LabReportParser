import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute("""
    SELECT r.is_delete, COUNT(*) 
    FROM LabResult lr 
    JOIN Report r ON lr.report_id = r.report_id 
    WHERE lr.item_id = 37
    GROUP BY r.is_delete
""")
results = c.fetchall()
print("谷丙转氨酶记录按is_delete分组:")
for r in results:
    print(f"is_delete={r[0]}, 数量={r[1]}")

c.execute("""
    SELECT DISTINCT r.report_id, r.file_name, r.is_delete, r.sample_time
    FROM LabResult lr 
    JOIN Report r ON lr.report_id = r.report_id 
    WHERE lr.item_id = 37
    ORDER BY r.sample_time
""")
results = c.fetchall()
print("\n谷丙转氨酶相关的不同报告:")
for r in results:
    print(f"report_id={r[0][:20]}, file_name={r[1][:30]}, is_delete={r[2]}, sample_time={r[3]}")

conn.close()
