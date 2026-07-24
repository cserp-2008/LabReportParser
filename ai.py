import base64
import json
import fitz  # PyMuPDF，核心PDF解析库
from openai import OpenAI
from typing import List

# ===================== 配置区 =====================
ARK_API_KEY = "d82024ee-bcc0-4452-bb76-0715fb85b611"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
VISION_MODEL = "doubao-vision-pro"
TEXT_MODEL = "doubao-pro-32k"
# 化验单提取固定Prompt
EXTRACT_PROMPT = """你是专业医学检验数据提取助手，只解析血常规、生化、血氨等化验单。
严格规则：
1. 提取5个字段：name(指标名称)、value(检测结果)、unit(单位)、reference(参考区间)、abnormal(升高↑=H，降低↓=L，正常=N)
2. 仅输出标准JSON数组，禁止多余文字、解释、markdown、```标记
3. 数值、单位严格和原文一致；无参考范围填空字符串
输出示例：
[
  {"name":"血氨","value":"50","unit":"μmol/L","reference":"18-72","abnormal":"N"}
]
"""
# ==================================================

client = OpenAI(api_key=ARK_API_KEY, base_url=BASE_URL)

def is_scanned_pdf(pdf_path: str) -> tuple[bool, str]:
    """
    判断PDF是扫描图片版 还是 纯文本版
    return (是否扫描件, 提取到的全部文本)
    """
    doc = fitz.open(pdf_path)
    full_text = ""
    total_text_len = 0
    page_image_count = 0

    for page in doc:
        # 1. 提取页面文本
        page_text = page.get_text()
        full_text += page_text
        total_text_len += len(page_text.strip())

        # 2. 统计页面内图片数量
        img_list = page.get_images(full=True)
        page_image_count += len(img_list)

    doc.close()
    # 判断逻辑：文本极少 + 存在大量图片 = 扫描图片PDF
    # 阈值可根据业务调整：总文本小于100字符判定为扫描件
    is_scan = total_text_len < 100 and page_image_count > 0
    return is_scan, full_text

def pdf_page_to_base64(pdf_path: str) -> List[str]:
    """扫描PDF：每页转图片，输出base64列表"""
    doc = fitz.open(pdf_path)
    base64_list = []
    for page in doc:
        # 提高分辨率，保证化验单文字清晰
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("jpeg")
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        base64_list.append(b64)
    doc.close()
    return base64_list

def extract_by_text(text: str):
    """纯文本PDF：调用文本模型提取指标"""
    resp = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": EXTRACT_PROMPT + "\n化验单内容：\n" + text}],
        temperature=0.0,
        max_tokens=4096
    )
    raw = resp.choices[0].message.content.strip()
    return json.loads(raw)

def extract_by_image(base64_img: str):
    """单张图片base64调用视觉模型"""
    resp = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACT_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                ]
            }
        ],
        temperature=0.0,
        max_tokens=4096
    )
    raw = resp.choices[0].message.content.strip()
    return json.loads(raw)

def parse_pdf_lab_report(pdf_file_path: str):
    """统一入口：自动区分PDF类型并提取化验单指标"""
    # 第一步：判断PDF类型
    scan_flag, pdf_text = is_scanned_pdf(pdf_file_path)
    all_result = []

    if not scan_flag:
        # 纯文本PDF，直接文本解析
        print("识别为【纯文本PDF】，使用文本模型提取")
        all_result = extract_by_text(pdf_text)
    else:
        # 扫描图片PDF，逐页转图识别，合并结果
        print("识别为【扫描图片PDF】，逐页调用视觉模型")
        img_b64_list = pdf_page_to_base64(pdf_file_path)
        for idx, b64 in enumerate(img_b64_list):
            page_data = extract_by_image(b64)
            all_result.extend(page_data)
            print(f"第{idx+1}页解析完成")
    
    return all_result

if __name__ == "__main__":
    # 替换为你的PDF文件路径
    pdf_path = r"D:\private\CS\CS\LabReport\2026-01-07生化全套.pdf"
    result = parse_pdf_lab_report(pdf_path)
    # 格式化输出结构化指标
    print(json.dumps(result, indent=2, ensure_ascii=False))