import fitz
import os

pdf_dir = r'd:\private\CS\CS\src\labreptemplate\NBMC'
output_dir = r'd:\private\CS\CS\src\labreptemplate\NBMC\images'
os.makedirs(output_dir, exist_ok=True)

for fname in os.listdir(pdf_dir):
    if not fname.endswith('.pdf'):
        continue
    path = os.path.join(pdf_dir, fname)
    doc = fitz.open(path)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=300)
        out_path = os.path.join(output_dir, fname.replace('.pdf', f'_p{i+1}.png'))
        pix.save(out_path)
        print(f'Saved: {out_path} ({pix.width}x{pix.height})')
    doc.close()
