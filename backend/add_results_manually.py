import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

blood_type_results = [
    ('2026-05-06血型+不规则抗体.pdf', 'ABO血型鉴定', 'A型', '', ''),
    ('2026-05-06血型+不规则抗体.pdf', 'RH血型RhD鉴定', '阳性', '', ''),
    ('2026-05-06血型+不规则抗体.pdf', '血型单特异性抗体鉴定', '阴性', '', ''),
]

blood_culture_results = [
    ('2026-05-06血培养双侧双瓶（2需氧+2厌氧）.pdf', '血培养结果', '5天无菌生长，未检出真菌', '', ''),
    ('2026-05-06血培养双侧双瓶（2需氧+2厌氧）.pdf', '厌氧菌培养', '5天无厌氧菌生长', '', ''),
]

for file_name, item_name, value, unit, ref in blood_type_results:
    c.execute("SELECT report_id, file_name, storage_path FROM report WHERE file_name = ? AND is_delete=0", (file_name,))
    result = c.fetchone()
    if not result:
        print(f'未找到报告: {file_name}')
        continue
    
    report_id, source_file, source_path = result
    
    c.execute("SELECT COUNT(*) FROM LabResult WHERE report_id = ? AND raw_item_name = ?", (report_id, item_name))
    count = c.fetchone()[0]
    if count > 0:
        print(f'已存在: {file_name} - {item_name}')
        continue
    
    c.execute('''
        INSERT INTO LabResult (report_id, page_id, raw_item_name, raw_value, unit, reference_text, source_file, source_path)
        VALUES (?, 1, ?, ?, ?, ?, ?, ?)
    ''', (report_id, item_name, value, unit, ref, source_file, source_path))
    print(f'添加: {file_name} - {item_name}: {value}')

for file_name, item_name, value, unit, ref in blood_culture_results:
    c.execute("SELECT report_id, file_name, storage_path FROM report WHERE file_name = ? AND is_delete=0", (file_name,))
    result = c.fetchone()
    if not result:
        print(f'未找到报告: {file_name}')
        continue
    
    report_id, source_file, source_path = result
    
    c.execute("SELECT COUNT(*) FROM LabResult WHERE report_id = ? AND raw_item_name = ?", (report_id, item_name))
    count = c.fetchone()[0]
    if count > 0:
        print(f'已存在: {file_name} - {item_name}')
        continue
    
    c.execute('''
        INSERT INTO LabResult (report_id, page_id, raw_item_name, raw_value, unit, reference_text, source_file, source_path)
        VALUES (?, 1, ?, ?, ?, ?, ?, ?)
    ''', (report_id, item_name, value, unit, ref, source_file, source_path))
    print(f'添加: {file_name} - {item_name}: {value}')

conn.commit()
conn.close()

print('\n手动添加完成！')