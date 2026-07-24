import os

file_path = '../storage/report/2026/07/c0dcb892d47c4783bb545f4dc518e1f8_2026-06-17EBV-DNAEB病毒.pdf'
full_path = os.path.abspath(file_path)
print(f'文件路径: {full_path}')
print(f'文件存在: {os.path.exists(full_path)}')

from parser.pdf_parser import PDFParser

parser = PDFParser()
pages = parser.parse(full_path)
print(f'\nPDF文本内容:')
for i, page in enumerate(pages):
    print(f'\n=== 第{i+1}页 ===')
    print(page.text[:3000])