import httpx
import base64
import json
import os
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from db.models import AIConfig, Report, ReportPage, LabResult
from utils.file_utils import generate_report_id, get_storage_path, calculate_md5
from parser.pdf_parser import PDFParser
from parser.hospital_detector import HospitalDetector
from parser.jph_parser import JPHParser
from parser.nbmc_parser import NBMCParser
from parser.nsh_parser import NSHParser

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = """你是一个专业的医疗化验单识别助手。请仔细阅读化验单图片中的内容，并提取所有检验指标数据。

要求：
1. 识别患者信息：姓名、性别、年龄、采集时间、报告时间、医院名称
2. 识别所有检验项目，每项包含：项目名称、缩写(如有)、结果值、单位、参考范围、异常标记(↑↓等)
3. 结果必须是严格的JSON格式，不要包含任何其他文字或Markdown格式
4. 如果某项数据缺失，对应字段设为null

JSON格式示例：
{
  "patient": {
    "name": "张三",
    "gender": "男",
    "age": "35岁",
    "sample_time": "2026-05-08 10:30",
    "report_time": "2026-05-08 14:00",
    "hospital": "江苏省人民医院"
  },
  "items": [
    {
      "name": "白细胞计数",
      "code": "WBC",
      "result": "7.5",
      "unit": "×10⁹/L",
      "ref_range": "4.0-10.0",
      "flag": null
    },
    {
      "name": "谷丙转氨酶",
      "code": "ALT",
      "result": "45",
      "unit": "U/L",
      "ref_range": "0-40",
      "flag": "↑"
    }
  ]
}

请直接返回JSON，不要有任何解释或额外文字！"""


class AIService:
    def __init__(self, db: Session):
        self.db = db
        self.config = self._get_active_config()
        self.client = None
        if self.config:
            self.client = httpx.Client(
                base_url=self.config.base_url,
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=120.0
            )

    def _get_active_config(self) -> Optional[AIConfig]:
        return self.db.query(AIConfig).filter(AIConfig.is_active == 1).first()

    def has_config(self) -> bool:
        return self.config is not None

    def save_config(self, api_key: str, base_url: str, model_name: str, prompt: str = None):
        existing = self.db.query(AIConfig).filter(AIConfig.is_active == 1).first()
        if existing:
            existing.api_key = api_key
            existing.base_url = base_url
            existing.model_name = model_name
            existing.prompt = prompt or DEFAULT_PROMPT
        else:
            config = AIConfig(
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                prompt=prompt or DEFAULT_PROMPT
            )
            self.db.add(config)
        self.db.commit()
        self.config = self._get_active_config()
        if self.config:
            self.client = httpx.Client(
                base_url=self.config.base_url,
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=120.0
            )
        return self.config

    def get_config(self) -> Optional[AIConfig]:
        return self.config

    def _pdf_to_images(self, pdf_path: str) -> List[str]:
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path)
            image_paths = []
            for i, image in enumerate(images):
                img_path = f"{pdf_path}_page_{i+1}.png"
                image.save(img_path, 'PNG')
                image_paths.append(img_path)
            return image_paths
        except ImportError:
            logger.warning("pdf2image未安装，请安装：pip install pdf2image")
            return []
        except Exception as e:
            logger.error(f"PDF转图片失败: {e}")
            if "poppler" in str(e).lower():
                logger.warning("需要安装poppler工具。Windows: choco install poppler 或下载 https://github.com/oschwartz10612/poppler-windows/releases")
            return []

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _call_ai(self, image_base64: str, page_num: int = 1) -> Dict:
        if not self.client or not self.config:
            raise Exception("AI配置未设置")

        prompt = self.config.prompt or DEFAULT_PROMPT

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{prompt}\n\n这是化验单第 {page_num} 页的图片，请识别其中的内容。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]

        try:
            response = self.client.post(
                "/chat/completions",
                json={
                    "model": self.config.model_name,
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                    "max_tokens": 8000,
                    "temperature": 0.1
                }
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"AI返回JSON解析失败: {content}")
            raise Exception(f"AI返回格式错误: {str(e)}")
        except Exception as e:
            logger.error(f"AI调用失败: {e}")
            raise

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        try:
            parser = PDFParser()
            pages = parser.parse(pdf_path)
            return "\n".join(p.text for p in pages)
        except Exception as e:
            logger.error(f"PDF文本提取失败: {e}")
            return ""

    def parse_report(self, pdf_path: str, task_id: str, storage_root: str) -> Dict:
        if not self.has_config():
            return {"error": "AI配置未设置"}

        results = []
        patient_info = {}
        use_fallback = False
        fallback_reason = ""

        image_paths = self._pdf_to_images(pdf_path)
        if not image_paths:
            fallback_reason = "PDF转图片失败，尝试纯文本模式"
            logger.warning(fallback_reason)
            text = self._extract_text_from_pdf(pdf_path)
            if text:
                messages = [
                    {
                        "role": "user",
                        "content": f"{self.config.prompt}\n\n化验单文本内容如下，请提取数据：\n\n{text}"
                    }
                ]
                try:
                    response = self.client.post(
                        "/chat/completions",
                        json={
                            "model": self.config.model_name,
                            "messages": messages,
                            "response_format": {"type": "json_object"},
                            "max_tokens": 8000,
                            "temperature": 0.1
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    ai_result = json.loads(content)
                    patient_info = ai_result.get("patient", {})
                    results = ai_result.get("items", [])
                    page_count = 1
                except Exception as e:
                    fallback_reason = f"大模型调用失败({str(e)})，使用传统解析器"
                    logger.warning(fallback_reason)
                    use_fallback = True
            else:
                fallback_reason = "无法提取PDF内容，使用传统解析器"
                logger.warning(fallback_reason)
                use_fallback = True
        else:
            page_count = len(image_paths)
            try:
                for i, img_path in enumerate(image_paths):
                    logger.info(f"正在识别第 {i+1}/{page_count} 页...")
                    image_base64 = self._encode_image(img_path)
                    ai_result = self._call_ai(image_base64, i+1)

                    if i == 0:
                        patient_info = ai_result.get("patient", {})

                    page_items = ai_result.get("items", [])
                    for item in page_items:
                        item["page_num"] = i + 1
                    results.extend(page_items)
            except Exception as e:
                fallback_reason = f"大模型调用失败({str(e)})，使用传统解析器"
                logger.warning(fallback_reason)
                use_fallback = True
            finally:
                for img_path in image_paths:
                    if os.path.exists(img_path):
                        try:
                            os.remove(img_path)
                        except:
                            pass

        if use_fallback:
            return self._fallback_parse(pdf_path, task_id, storage_root)

        report_id = generate_report_id()
        file_name = os.path.basename(pdf_path)
        file_size = os.path.getsize(pdf_path)
        file_md5 = calculate_md5(pdf_path)
        storage_path = get_storage_path(storage_root, report_id, file_name)

        if pdf_path != storage_path:
            import shutil
            shutil.copy2(pdf_path, storage_path)

        report = Report(
            report_id=report_id,
            task_id=task_id,
            file_name=file_name,
            file_type=file_name.split('.')[-1].lower(),
            file_size=file_size,
            file_md5=file_md5,
            storage_path=storage_path,
            page_count=page_count,
            quality_score=0,
            review_status=0,
            patient_name=patient_info.get("name"),
            gender=patient_info.get("gender"),
            age=patient_info.get("age"),
        )
        self.db.add(report)
        self.db.commit()

        from core.utils import parse_datetime
        if patient_info.get("sample_time"):
            report.sample_time = parse_datetime(patient_info["sample_time"])
        if patient_info.get("report_time"):
            report.report_time = parse_datetime(patient_info["report_time"])
        if patient_info.get("hospital"):
            from db.models import Hospital
            hospital = self.db.query(Hospital).filter(
                Hospital.hospital_name.like(f"%{patient_info['hospital']}%")
            ).first()
            if hospital:
                report.hospital_id = hospital.hospital_id
        self.db.commit()

        for page_num in range(1, page_count + 1):
            page = ReportPage(
                report_id=report_id,
                page_no=page_num
            )
            self.db.add(page)
        self.db.commit()

        pages = self.db.query(ReportPage).filter(ReportPage.report_id == report_id).all()
        page_map = {p.page_no: p for p in pages}

        result_count = 0
        for item in results:
            page_no = item.get("page_num", 1)
            page = page_map.get(page_no)
            if not page:
                continue

            lab_result = LabResult(
                report_id=report_id,
                page_id=page.page_id,
                raw_item_name=item.get("name", ""),
                raw_value=item.get("result", ""),
                unit=item.get("unit", ""),
                reference_text=item.get("ref_range", ""),
                flag=item.get("flag", ""),
                source_file=file_name,
                source_path=storage_path
            )

            try:
                from core.utils import parse_numeric
                lab_result.value_numeric = parse_numeric(item.get("result", ""))
            except:
                pass

            try:
                from core.utils import parse_reference_range
                ref_low, ref_high = parse_reference_range(item.get("ref_range", ""))
                lab_result.reference_low = ref_low
                lab_result.reference_high = ref_high
            except:
                pass

            self.db.add(lab_result)
            result_count += 1

        self.db.commit()

        return {
            "report_id": report_id,
            "patient": patient_info,
            "result_count": result_count,
            "page_count": page_count,
            "quality_score": 0,
            "ai_used": True
        }

    def _fallback_parse(self, pdf_path: str, task_id: str, storage_root: str) -> Dict:
        """使用传统解析器进行降级解析"""
        pdf_parser = PDFParser()
        pages = pdf_parser.parse(pdf_path)
        full_text = "\n".join(p.text for p in pages)
        full_coords_text = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)

        detector = HospitalDetector()
        hospital_name = detector.detect(full_text)

        if "明基" in (hospital_name or ""):
            parser = NBMCParser()
            use_coords = True
        elif "江苏省人民医院" in (hospital_name or ""):
            parser = JPHParser()
            use_coords = True
        elif "南京市第二医院" in (hospital_name or ""):
            parser = NSHParser()
            use_coords = True
        else:
            parser = JPHParser()
            use_coords = False

        if use_coords and full_coords_text:
            report = parser.parse(full_coords_text)
        else:
            report = parser.parse(full_text)

        report_id = generate_report_id()
        file_name = os.path.basename(pdf_path)
        file_size = os.path.getsize(pdf_path)
        file_md5 = calculate_md5(pdf_path)
        storage_path = get_storage_path(storage_root, report_id, file_name)

        if pdf_path != storage_path:
            import shutil
            shutil.copy2(pdf_path, storage_path)

        from parser.service import ParseService
        
        db_report = Report(
            report_id=report_id,
            task_id=task_id,
            file_name=file_name,
            file_type=file_name.split('.')[-1].lower(),
            file_size=file_size,
            file_md5=file_md5,
            storage_path=storage_path,
            page_count=getattr(report, 'page_count', 1),
            quality_score=getattr(report, 'quality_score', 0),
            review_status=0,
            patient_name=getattr(report, 'patient_name', None),
            gender=getattr(report, 'gender', None),
            age=getattr(report, 'age', None),
            sample_time=ParseService._parse_datetime(None, str(getattr(report, 'sample_time', ''))) if getattr(report, 'sample_time', None) else None,
            report_time=ParseService._parse_datetime(None, str(getattr(report, 'report_time', ''))) if getattr(report, 'report_time', None) else None,
            hospital_id=getattr(report, 'hospital_id', None),
        )
        self.db.add(db_report)
        self.db.commit()

        for page_no in range(1, (getattr(report, 'page_count', 1)) + 1):
            page = ReportPage(
                report_id=report_id,
                page_no=page_no
            )
            self.db.add(page)
        self.db.commit()

        pages = self.db.query(ReportPage).filter(ReportPage.report_id == report_id).all()
        page_map = {p.page_no: p for p in pages}

        result_count = 0
        for item in report.results:
            page_no = getattr(item, 'page_num', 1)
            page = page_map.get(page_no, page_map.get(1))
            if not page:
                continue

            lab_result = LabResult(
                report_id=report_id,
                page_id=page.page_id,
                raw_item_name=item.raw_item_name,
                raw_value=item.raw_value,
                unit=item.unit,
                reference_text=item.reference_text,
                flag=item.flag,
                source_file=file_name,
                source_path=storage_path,
                value_numeric=item.value_numeric,
                reference_low=item.reference_low,
                reference_high=item.reference_high,
            )
            self.db.add(lab_result)
            result_count += 1

        self.db.commit()

        patient_info = {
            "name": getattr(report, 'patient_name', None),
            "gender": getattr(report, 'gender', None),
            "age": getattr(report, 'age', None),
            "sample_time": str(getattr(report, 'sample_time', None)) if getattr(report, 'sample_time', None) else None,
            "report_time": str(getattr(report, 'report_time', None)) if getattr(report, 'report_time', None) else None,
        }

        return {
            "report_id": report_id,
            "patient": patient_info,
            "result_count": result_count,
            "page_count": getattr(report, 'page_count', 1),
            "quality_score": getattr(report, 'quality_score', 0),
            "ai_used": False,
            "fallback_reason": "大模型不可用，已自动使用传统解析器"
        }