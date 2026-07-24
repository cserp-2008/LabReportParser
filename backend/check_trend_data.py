import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM LabResult WHERE item_id = 37")
result = c.fetchone()
print("谷丙转氨酶(item_id=37)在LabResult中的记录数:", result[0])

c.execute("SELECT COUNT(*) FROM LabResult WHERE raw_item_name LIKE '%谷丙转氨酶%'")
result = c.fetchone()
print("raw_item_name包含谷丙转氨酶的记录数:", result[0])

c.execute("SELECT COUNT(*) FROM LabResult WHERE raw_item_name LIKE '%ALT%'")
result = c.fetchone()
print("raw_item_name包含ALT的记录数:", result[0])

c.execute("SELECT item_id, raw_item_name, raw_value, value_numeric FROM LabResult WHERE raw_item_name LIKE '%谷丙转氨酶%' LIMIT 10")
results = c.fetchall()
print("\n谷丙转氨酶相关记录示例:")
for r in results:
    print(r)

conn.close()
