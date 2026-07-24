import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute("SELECT item_id, item_name, abbr, standard_unit FROM LabItem WHERE item_name LIKE '%谷丙转氨酶%'")
result = c.fetchone()
print("谷丙转氨酶:", result)

c.execute("SELECT item_id, item_name, abbr, standard_unit FROM LabItem WHERE item_name LIKE '%谷草转氨酶%'")
result = c.fetchone()
print("谷草转氨酶:", result)

c.execute("SELECT item_id, item_name, abbr, standard_unit FROM LabItem WHERE item_name LIKE '%血糖%'")
result = c.fetchone()
print("血糖:", result)

c.execute("SELECT COUNT(DISTINCT item_id) FROM LabResult")
result = c.fetchone()
print("LabResult中不同item_id数量:", result[0])

conn.close()
