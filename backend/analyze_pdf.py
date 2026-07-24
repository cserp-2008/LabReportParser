import fitz
import os

pdf_dir = r'd:\private\CS\CS\src\labreptemplate\NBMC'
for fname in os.listdir(pdf_dir):
    if not fname.endswith('.pdf'):
        continue
    path = os.path.join(pdf_dir, fname)
    doc = fitz.open(path)
    page = doc[0]

    blocks = page.get_text('blocks')
    print(f'===== {fname} =====')
    print(f'Page size: {page.rect}')
    print(f'Blocks count: {len(blocks)}')
    for b in blocks[:80]:
        print(f'  bbox=({b[0]:.0f},{b[1]:.0f},{b[2]:.0f},{b[3]:.0f}) text={repr(b[4][:120])}')
    print()
    doc.close()
