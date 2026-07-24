"""查看OCR原始坐标数据"""
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
        width = right - left
        height = bottom - top
        print(f'  ({left:.0f},{top:.0f},{width:.0f}x{height:.0f}) conf={conf:.2f} text={repr(text)}')
    print()
