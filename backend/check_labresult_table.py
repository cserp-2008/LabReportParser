import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute('PRAGMA table_info(LabResult)')
print('LabResult表结构:')
for col in c.fetchall():
    print(f'  {col[1]} ({col[2]}) - nullable: {col[3]==0}')

conn.close()