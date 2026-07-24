"""OCR提取南京明基医院化验单PDF的文本和坐标"""
import os
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)

pdf_dir = r'd:\private\CS\CS\src\labreptemplate\NBMC\images'
for fname in sorted(os.listdir(pdf_dir)):
    if not fname.endswith('.png'):
        continue
    img_path = os.path.join(pdf_dir, fname)
    print(f'===== {fname} =====')
    
    result = ocr.ocr(img_path, cls=True)
    
    for line in result[0]:
        bbox, (text, conf) = line
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        left = min(xs)
        top = min(ys)
        right = max(xs)
        bottom = max(ys)
        print(f'  ({left:.0f},{top:.0f},{right:.0f},{bottom:.0f}) conf={conf:.2f} text={text}')
    print()
