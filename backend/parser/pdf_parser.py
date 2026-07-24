"""PDF 文本提取模块

支持文字 PDF 直接提取文本，扫描 PDF 通过 PyMuPDF 渲染 + PaddleOCR 识别。
依据设计说明书第 6 章 OCR 与文档解析引擎设计。
"""
import os
import re
import logging
import threading
from typing import List, Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# 解决 OpenMP 冲突
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

logger = logging.getLogger(__name__)

# PaddleOCR 实例惰性初始化（全局单例）
_ocr_instance = None
_ocr_lock = threading.Lock()


def _get_ocr():
    """惰性初始化 PaddleOCR 单例"""
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR
        _ocr_instance = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        logger.info("PaddleOCR 初始化完成")
    return _ocr_instance


class PageText:
    """单页文本提取结果"""

    def __init__(self, page_no: int, text: str, width: int = 800, height: int = 600, ocr_coords_text: str = ""):
        self.page_no = page_no
        self.text = text
        self.width = width
        self.height = height
        self.lines = [line.strip() for line in text.split("\n") if line.strip()]
        self.ocr_used = False
        self.ocr_coords_text = ocr_coords_text

    def __repr__(self):
        return f"<PageText page={self.page_no} lines={len(self.lines)} ocr={self.ocr_used}>"


class PDFParser:
    """PDF 文本提取器

    文字 PDF: 使用 pdfplumber 提取文本
    扫描 PDF / 图片: 使用 PyMuPDF 渲染为图片 + PaddleOCR 识别
    """

    SUPPORTED_PDF_EXT = {".pdf"}
    SUPPORTED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

    # 判定需要 OCR 的阈值：有效文字字符数低于此值视为扫描件
    OCR_TEXT_THRESHOLD = 10

    @classmethod
    def is_supported_file(cls, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in cls.SUPPORTED_PDF_EXT or ext in cls.SUPPORTED_IMAGE_EXT

    @classmethod
    def is_image(cls, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in cls.SUPPORTED_IMAGE_EXT

    @classmethod
    def is_pdf(cls, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in cls.SUPPORTED_PDF_EXT

    def parse(self, file_path: str) -> List[PageText]:
        """解析文件，返回每页文本列表

        Args:
            file_path: 文件绝对路径

        Returns:
            List[PageText]: 每页文本内容
        """
        if not os.path.exists(file_path):
            return []

        if self.is_image(file_path):
            return self._parse_image(file_path)

        if self.is_pdf(file_path):
            return self._parse_pdf(file_path)

        return []

    def _parse_pdf(self, file_path: str) -> List[PageText]:
        """解析 PDF

        优先使用 pdfplumber 提取文字层；
        若文字层为空或仅含 (cid:N) 等无法解码的字符，回退到 OCR。
        """
        pages = []

        # 1. 先用 pdfplumber 提取文字层
        plumber_pages = self._extract_with_pdfplumber(file_path)

        # 2. 对需要 OCR 的页面进行 OCR
        for pt in plumber_pages:
            if self._needs_ocr(pt.text):
                logger.info(f"页面 {pt.page_no} 文字层无效，启用 OCR")
                ocr_text, coords_text = self._ocr_pdf_page(file_path, pt.page_no)
                if ocr_text:
                    pt.text = ocr_text
                    pt.lines = [l.strip() for l in ocr_text.split("\n") if l.strip()]
                    pt.ocr_used = True
                    pt.ocr_coords_text = coords_text
            pages.append(pt)

        if not pages:
            pages = [PageText(page_no=1, text="")]

        return pages

    def _extract_with_pdfplumber(self, file_path: str) -> List[PageText]:
        """使用 pdfplumber 提取每页文本"""
        pages: List[PageText] = []
        if pdfplumber is None:
            # 无 pdfplumber，尝试 PyMuPDF 提取文字
            return self._extract_with_fitz(file_path)

        try:
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    width = int(page.width) if page.width else 800
                    height = int(page.height) if page.height else 600
                    pages.append(PageText(page_no=i, text=text, width=width, height=height))
        except Exception as e:
            logger.warning(f"pdfplumber 解析失败 {file_path}: {e}")
            pages = self._extract_with_fitz(file_path)

        return pages

    def _extract_with_fitz(self, file_path: str) -> List[PageText]:
        """使用 PyMuPDF 提取每页文本"""
        pages: List[PageText] = []
        if fitz is None:
            return [PageText(page_no=1, text="")]

        try:
            doc = fitz.open(file_path)
            for i, page in enumerate(doc, start=1):
                text = page.get_text() or ""
                rect = page.rect
                pages.append(PageText(
                    page_no=i, text=text,
                    width=int(rect.width), height=int(rect.height),
                ))
            doc.close()
        except Exception as e:
            logger.error(f"PyMuPDF 解析失败 {file_path}: {e}")
            pages = [PageText(page_no=1, text="")]

        return pages

    def _needs_ocr(self, text: str) -> bool:
        """判断是否需要 OCR：有效字符过少或全是 CID 乱码"""
        if not text:
            return True
        # 去除 (cid:N) 模式后的有效内容
        cleaned = re.sub(r"\(cid:\d+\)", "", text).strip()
        # 去除空白后的有效字符数
        effective = re.sub(r"\s+", "", cleaned)
        return len(effective) < self.OCR_TEXT_THRESHOLD

    def _ocr_pdf_page(self, file_path: str, page_no: int, dpi: int = 200) -> str:
        """将 PDF 指定页面渲染为图片并 OCR

        Args:
            file_path: PDF 路径
            page_no: 页码（从 1 开始）
            dpi: 渲染分辨率

        Returns:
            OCR 提取的文本
        """
        if fitz is None:
            logger.warning("PyMuPDF 不可用，无法渲染 PDF 页面")
            return ""

        try:
            doc = fitz.open(file_path)
            if page_no < 1 or page_no > len(doc):
                doc.close()
                return ""
            page = doc[page_no - 1]
            pix = page.get_pixmap(dpi=dpi)
            img_path = file_path + f".page{page_no}.png"
            pix.save(img_path)
            doc.close()

            text, coords_text = self._ocr_image(img_path)

            # 清理临时图片
            try:
                os.remove(img_path)
            except OSError:
                pass

            return text, coords_text
        except Exception as e:
            logger.error(f"OCR 渲染失败 {file_path} page={page_no}: {e}")
            return "", ""

    def _parse_image(self, file_path: str) -> List[PageText]:
        """直接对图片进行 OCR"""
        text, coords_text = self._ocr_image(file_path)
        pt = PageText(page_no=1, text=text, ocr_coords_text=coords_text)
        pt.ocr_used = True
        return [pt]

    def _ocr_image(self, img_path: str) -> tuple:
        """使用 PaddleOCR 识别图片文字

        将识别结果按位置重建为按行排列的文本。
        
        Returns:
            (text, coords_text): 重组后的文本行 和 坐标文本
        """
        try:
            ocr = _get_ocr()
        except Exception as e:
            logger.error(f"PaddleOCR 初始化失败: {e}")
            return ""

        try:
            with _ocr_lock:
                result = ocr.ocr(img_path, cls=True)
        except Exception as e:
            logger.error(f"PaddleOCR 识别失败 {img_path}: {e}")
            return "", ""

        if not result or not result[0]:
            return "", ""

        # PaddleOCR 返回 [[box, (text, conf)], ...]
        lines = self._reconstruct_lines(result[0])
        coords_text = self._format_coords_text(result[0])
        return "\n".join(lines), coords_text

    def _format_coords_text(self, ocr_items) -> str:
        """将OCR结果格式化为坐标文本

        返回格式：(x,y,w,h) conf=0.99 text=内容
        """
        lines = []
        for item in ocr_items:
            box, (text, conf) = item
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            left = min(xs)
            top = min(ys)
            right = max(xs)
            bottom = max(ys)
            width = right - left
            height = bottom - top
            lines.append(f"({left:.0f},{top:.0f},{width:.0f}x{height:.0f}) conf={conf:.2f} text={text}")
        return "\n".join(lines)

    def _reconstruct_lines(self, ocr_items, y_threshold: float = 15.0) -> List[str]:
        """将 OCR 文本块按位置重组为行

        Args:
            ocr_items: PaddleOCR 返回的 [box, (text, conf)] 列表
            y_threshold: Y 坐标差异小于此值视为同一行

        Returns:
            按从上到下、从左到右排序的文本行列表
        """
        items = []
        for item in ocr_items:
            box, (text, conf) = item
            # box 是 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            ys = [p[1] for p in box]
            xs = [p[0] for p in box]
            center_y = sum(ys) / len(ys)
            center_x = sum(xs) / len(xs)
            items.append({
                "text": text.strip(),
                "y": center_y,
                "x": center_x,
                "conf": conf,
            })

        if not items:
            return []

        # 按 Y 排序
        items.sort(key=lambda it: it["y"])

        # 按行分组
        lines = []
        current_line = [items[0]]
        for it in items[1:]:
            if abs(it["y"] - current_line[0]["y"]) <= y_threshold:
                current_line.append(it)
            else:
                lines.append(current_line)
                current_line = [it]
        lines.append(current_line)

        # 每行按 X 排序后合并文本
        result = []
        for line in lines:
            line.sort(key=lambda it: it["x"])
            # 合并同行的文本块；如果两个相邻块之间有空隙则加空格
            text_parts = []
            for it in line:
                if text_parts and not text_parts[-1].endswith(("-", "：", ":", "（", "(", "、")):
                    text_parts.append(" ")
                text_parts.append(it["text"])
            line_text = "".join(text_parts).strip()
            if line_text:
                result.append(line_text)

        return result
