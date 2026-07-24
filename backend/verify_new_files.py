import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

new_files = [
    '2026-05-06乙型肝炎DNA定量.pdf',
    '2026-05-06乙肝五项.pdf',
    '2026-05-06脂肪酶.pdf',
    '2026-05-06血型+不规则抗体.pdf',
    '2026-05-06血培养双侧双瓶（2需氧+2厌氧）.pdf',
    '2026-05-11一般细菌培养及鉴定(腹水)屎肠球菌.pdf'
]

print('=== 新上传文件解析结果 ===\n')

for file_name in new_files:
    c.execute("SELECT report_id, hospital_id, patient_name, sample_time, report_time FROM report WHERE file_name = ? AND is_delete=0", (file_name,))
    result = c.fetchone()
    
    if not result:
        print(f'❌ {file_name} - 未找到报告')
        print()
        continue
    
    report_id = result[0]
    hospital_id = result[1]
    
    c.execute('SELECT hospital_name FROM Hospital WHERE hospital_id = ?', (hospital_id,))
    hospital_name = c.fetchone()[0] if hospital_id else '未知'
    
    c.execute('SELECT raw_item_name, raw_value, unit FROM LabResult WHERE report_id = ?', (report_id,))
    results = c.fetchall()
    
    print(f'📄 {file_name}')
    print(f'   医院: {hospital_name}')
    print(f'   患者: {result[2] or "未知"}')
    print(f'   指标数: {len(results)}')
    
    if results:
        print('   指标:')
        for r in results:
            print(f'     - {r[0]}: {r[1]} {r[2]}')
    else:
        print('   ❌ 未识别出指标')
    
    print()

conn.close()