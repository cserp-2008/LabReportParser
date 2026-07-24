"""测试南京明基医院专用解析器（使用坐标数据）"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.pdf_parser import PDFParser
from parser.nbmc_parser import NBMCParser

pdf_dir = r'd:\private\CS\CS\src\labreptemplate\NBMC'
pdf_parser = PDFParser()
nbmc_parser = NBMCParser()

for fname in sorted(os.listdir(pdf_dir)):
    if not fname.endswith('.pdf'):
        continue
    
    path = os.path.join(pdf_dir, fname)
    print(f'===== {fname} =====')
    
    pages = pdf_parser.parse(path)
    if not pages:
        print('  无法解析')
        continue
    
    full_coords_text = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)
    parsed = nbmc_parser.parse(full_coords_text)
    
    print(f'  患者姓名: {parsed.patient_name}')
    print(f'  性别: {parsed.gender}')
    print(f'  年龄: {parsed.age}')
    print(f'  采样时间: {parsed.sample_time}')
    print(f'  报告时间: {parsed.report_time}')
    print(f'  医院: {parsed.hospital_name}')
    print(f'  指标数: {len(parsed.results)}')
    print(f'  质量分: {parsed.quality_score:.1f}')
    print()
    
    print('  检验结果:')
    for i, result in enumerate(parsed.results[:30], 1):
        flag = result.flag if result.flag else ''
        ref = f'{result.reference_low}-{result.reference_high}' if result.reference_low else result.reference_text or ''
        print(f'    {i}. {result.raw_item_name} = {result.raw_value} {result.unit or ""} {flag} ref={ref}')
    
    if len(parsed.results) > 30:
        print(f'    ... 还有 {len(parsed.results) - 30} 项')
    
    print()
