import sqlite3

conn = sqlite3.connect('labreport.db')
c = conn.cursor()

c.execute("""
SELECT 
    r.report_id,
    r.file_name,
    r.hospital_id,
    h.hospital_name,
    r.patient_name,
    r.sample_time,
    r.report_time,
    r.page_count,
    COUNT(lr.result_id) as result_count,
    r.quality_score
FROM 
    Report r
LEFT JOIN 
    Hospital h ON r.hospital_id = h.hospital_id
LEFT JOIN 
    LabResult lr ON r.report_id = lr.report_id
WHERE 
    r.is_delete = 0
GROUP BY 
    r.report_id
ORDER BY 
    r.hospital_id, r.file_name
""")

reports = c.fetchall()

print(f'{"="*120}')
print(f'{"报告ID":<34} {"文件名":<60} {"医院":<20} {"指标数":>6} {"采样时间":<20} {"质量评分":>8}')
print(f'{"="*120}')

low_quality = []
no_hospital = []
no_sample_time = []
no_results = []

for r in reports:
    report_id, file_name, hospital_id, hospital_name, patient_name, sample_time, report_time, page_count, result_count, quality_score = r
    
    status = ""
    if hospital_id is None:
        no_hospital.append(report_id)
        status += "[无医院]"
    if sample_time is None or sample_time == "":
        no_sample_time.append(report_id)
        status += "[无采样时间]"
    if result_count == 0:
        no_results.append(report_id)
        status += "[无指标]"
    if result_count > 0 and result_count < 5:
        low_quality.append(report_id)
        status += "[指标少]"
    
    hospital_display = hospital_name if hospital_name else "未识别"
    print(f'{report_id:<34} {file_name:<60} {hospital_display:<20} {result_count:>6} {str(sample_time or ""):<20} {quality_score:>8.1f} {status}')

print(f'{"="*120}')
print(f'\n统计信息:')
print(f'  总报告数: {len(reports)}')
print(f'  无医院识别: {len(no_hospital)}')
print(f'  无采样时间: {len(no_sample_time)}')
print(f'  无指标: {len(no_results)}')
print(f'  指标数少于5个: {len(low_quality)}')

needs_reparse = list(set(no_hospital + no_results + low_quality))
print(f'  需要重新解析: {len(needs_reparse)}')

if needs_reparse:
    print(f'\n需要重新解析的报告ID:')
    for rid in needs_reparse:
        c.execute("SELECT file_name FROM Report WHERE report_id=?", (rid,))
        fname = c.fetchone()[0]
        print(f'  {rid} - {fname}')

conn.close()

with open('needs_reparse.txt', 'w') as f:
    for rid in needs_reparse:
        f.write(rid + '\n')
print(f'\n需要重新解析的报告ID已保存到 needs_reparse.txt')
