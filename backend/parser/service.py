"""解析调度服务

协调 PDF 提取、医院识别、检验结果解析、标准化，写入数据库。
依据设计说明书 1.8 核心业务总流程。
"""
import re
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
import os
import sys

from db.models import (
    Report, ReportPage, LabResult, Hospital, LabItem,
)
from .pdf_parser import PDFParser, PageText
from .lab_result_parser import LabResultParser, ParsedReport, ParsedResult
from .hospital_detector import HospitalDetector
from .standardizer import Standardizer
from .template_learner import TemplateLearner

try:
    from .nbmc_parser import NBMCParser
    NBMC_PARSER_AVAILABLE = True
except ImportError:
    NBMC_PARSER_AVAILABLE = False

try:
    from .jph_parser import JPHParser
    JPH_PARSER_AVAILABLE = True
except ImportError:
    JPH_PARSER_AVAILABLE = False

try:
    from .nsh_parser import NSHParser
    NSH_PARSER_AVAILABLE = True
except ImportError:
    NSH_PARSER_AVAILABLE = False

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ParseService:
    """解析调度服务"""

    def __init__(self, db: Session):
        self.db = db
        self.pdf_parser = PDFParser()
        self.lab_parser = LabResultParser()
        self.hospital_detector = HospitalDetector()
        self.standardizer = Standardizer(db)
        self.template_learner = TemplateLearner(db)

    def _generate_preview(self, report: Report, page_no: int) -> Optional[str]:
        """生成预览图片

        Args:
            report: 报告对象
            page_no: 页码

        Returns:
            预览图片路径，失败返回 None
        """
        try:
            import fitz
        except ImportError:
            return None

        file_path = report.storage_path
        if not os.path.exists(file_path):
            return None

        try:
            doc = fitz.open(file_path)
            if page_no < 1 or page_no > len(doc):
                doc.close()
                return None

            page = doc[page_no - 1]
            pix = page.get_pixmap(dpi=150)
            
            from core.config import config
            preview_root = config['storage_root']
            preview_dir = os.path.join(preview_root, "preview", report.report_id)
            os.makedirs(preview_dir, exist_ok=True)
            preview_path = os.path.join(preview_dir, f"page_{page_no}.png")
            
            pix.save(preview_path)
            doc.close()
            
            return preview_path
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"生成预览图片失败 {file_path} page={page_no}: {e}")
            return None

    def parse_report(self, report: Report, parser_code: Optional[str] = None) -> Dict:
        """解析单个报告

        Args:
            report: 报告 ORM 对象
            parser_code: 可选，手动指定解析引擎（common/jph/nbmc/nsh），不指定则自动识别医院

        Returns:
            解析结果摘要 dict
        """
        file_path = report.storage_path

        # 1. 提取每页文本
        pages: List[PageText] = self.pdf_parser.parse(file_path)

        # 删除旧页面数据，重新创建
        self.db.query(ReportPage).filter(ReportPage.report_id == report.report_id).delete()
        self.db.query(LabResult).filter(LabResult.report_id == report.report_id).delete()

        # 创建页面记录
        page_records = []
        for page_text in pages:
            preview_path = self._generate_preview(report, page_text.page_no)
            page = ReportPage(
                report_id=report.report_id,
                page_no=page_text.page_no,
                width=page_text.width,
                height=page_text.height,
                preview_image_path=preview_path,
            )
            self.db.add(page)
            page_records.append((page, page_text))
        self.db.flush()

        # 2. 合并全文解析患者信息和检验结果
        full_text = "\n".join(p.text for p in pages)
        full_coords_text = "\n".join(p.ocr_coords_text for p in pages if p.ocr_coords_text)
        parsed = self.lab_parser.parse(full_text)

        # 3. 识别医院（如果没有手动指定parser_code）
        hospital_name = None
        hospital_id = report.hospital_id
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"parse_report: report_id={report.report_id}, hospital_id={hospital_id}, parser_code={parser_code}")
        
        if hospital_id:
            hospital = self.db.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()
            if hospital:
                hospital_name = hospital.hospital_name
                if parser_code is None and hospital.parser_code:
                    parser_code = hospital.parser_code.lower()
                logger.info(f"parse_report: hospital_name={hospital_name}, parser_code={parser_code}")
        elif parser_code is None:
            hospital_name = self.hospital_detector.detect(full_text)
            if hospital_name:
                hospital_id = self._get_or_create_hospital(hospital_name)
                report.hospital_id = hospital_id
                hospital = self.db.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()
                if hospital and hospital.parser_code:
                    parser_code = hospital.parser_code.lower()
            else:
                parser_code = "common"

        # 4. 根据医院选择解析器
        lab_parser = self.lab_parser
        use_coords_text = False
        if NBMC_PARSER_AVAILABLE and (parser_code.lower() == "nbmc" or 
                                       (hospital_name and "明基" in hospital_name)):
            lab_parser = NBMCParser()
            use_coords_text = True
        elif JPH_PARSER_AVAILABLE and (parser_code.lower() == "jph" or 
                                       (hospital_name and "江苏省人民医院" in hospital_name) or
                                       (hospital_name and "江苏省人" in hospital_name and "院" in hospital_name)):
            lab_parser = JPHParser()
            use_coords_text = True
        elif NSH_PARSER_AVAILABLE and (parser_code.lower() == "nsh" or 
                                       (hospital_name and "南京市第二医院" in hospital_name)):
            lab_parser = NSHParser()
            use_coords_text = True

        # 重新用选定的解析器解析
        if use_coords_text and full_coords_text:
            if isinstance(lab_parser, NSHParser):
                parsed = lab_parser.parse(full_text, 1, full_coords_text)
            else:
                parsed = lab_parser.parse(full_coords_text)
        else:
            parsed = lab_parser.parse(full_text)

        # 5. 更新报告患者信息
        if parsed.patient_name:
            report.patient_name = parsed.patient_name
        if parsed.gender:
            report.gender = parsed.gender
        if parsed.age:
            report.age = parsed.age
        if parsed.sample_time:
            report.sample_time = self._parse_datetime(parsed.sample_time)
        if parsed.report_time:
            report.report_time = self._parse_datetime(parsed.report_time)

        # 6. 写入检验结果（标准化）
        for page, page_text in page_records:
            if isinstance(lab_parser, NSHParser) and page_text.ocr_coords_text:
                page_results = lab_parser.parse(page_text.text, page_text.page_no, page_text.ocr_coords_text).results
            else:
                parse_text = page_text.ocr_coords_text if use_coords_text and page_text.ocr_coords_text else page_text.text
                page_results = lab_parser.parse(parse_text, page_text.page_no).results
            for parsed_result in page_results:
                self._create_lab_result(report, page, parsed_result)

        # 6. 更新质量分和页数
        report.page_count = len(pages)
        report.quality_score = parsed.quality_score
        if parsed.quality_score < 85:
            report.review_status = 0  # 待复核
        else:
            report.review_status = 0  # 默认未复核

        self.db.commit()

        # 自动同步标准指标库（从本次解析结果中学习）
        try:
            from .labitem_sync import LabItemSync
            syncer = LabItemSync(self.db)
            syncer.sync()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"报告解析后同步标准指标库失败: {e}")

        result_count = self.db.query(LabResult).filter(
            LabResult.report_id == report.report_id
        ).count()

        return {
            "report_id": report.report_id,
            "page_count": len(pages),
            "result_count": result_count,
            "quality_score": report.quality_score,
            "hospital_id": hospital_id,
            "patient_name": report.patient_name,
        }

    def _get_or_create_hospital(self, hospital_name: str) -> Optional[int]:
        """获取或创建医院记录
        
        支持医院名称映射：
        - 人民医院 -> 江苏省人民医院
        - 省人民医院 -> 江苏省人民医院
        - 省人医 -> 江苏省人民医院
        - JPH -> 江苏省人民医院
        - 明基医院 -> 南京医科大学附属明基医院
        - 第二医院 -> 南京市第二医院
        """
        hospital_aliases = {
            "人民医院": "江苏省人民医院",
            "省人民医院": "江苏省人民医院",
            "省人医": "江苏省人民医院",
            "JPH": "江苏省人民医院",
            "南京医科大学第一附属医院": "江苏省人民医院",
            "南医大一附院": "江苏省人民医院",
            "明基医院": "南京医科大学附属明基医院",
            "市第二医院": "南京市第二医院",
            "肝病医院": "南京市第二医院",
        }

        normalized_name = hospital_aliases.get(hospital_name, hospital_name)

        existing = self.db.query(Hospital).filter(
            Hospital.hospital_name == normalized_name
        ).first()
        if existing:
            return existing.hospital_id

        parser_code_map = {
            "江苏省人民医院": "JPH",
            "南京医科大学附属明基医院": "NBMC",
            "南京市第二医院": "NSH",
        }
        parser_code = parser_code_map.get(normalized_name, "common")

        hospital = Hospital(
            hospital_name=normalized_name,
            parser_code=parser_code,
        )
        self.db.add(hospital)
        self.db.flush()
        return hospital.hospital_id

    def _create_lab_result(
        self,
        report: Report,
        page: ReportPage,
        parsed: ParsedResult,
    ):
        """创建检验结果记录，执行标准化映射和模板规则应用"""
        # 去重检查：同一报告同一指标不重复插入
        existing = self.db.query(LabResult).filter(
            LabResult.report_id == report.report_id,
            LabResult.raw_item_name == parsed.raw_item_name,
        ).first()
        if existing:
            return  # 已存在，跳过

        # 标准化映射
        standard_item = self.standardizer.standardize(parsed.raw_item_name, getattr(parsed, 'code', ''))
        item_id = standard_item.item_id if standard_item else None

        # 应用医院模板规则（人工学习到的特征）
        template_data = {"item_name": None, "unit": None, "reference_text": None}
        if report.hospital_id:
            template_data = self.template_learner.apply_template(
                report.hospital_id, parsed.raw_item_name
            )

        # 模板规则优先于OCR结果
        item_name = template_data.get("item_name") or (
            standard_item.item_name if standard_item else None
        )
        unit = template_data.get("unit") or parsed.unit
        reference_text = template_data.get("reference_text") or parsed.reference_text

        result = LabResult(
            report_id=report.report_id,
            page_id=page.page_id,
            item_id=item_id,
            raw_item_name=parsed.raw_item_name,
            raw_value=parsed.raw_value,
            value_numeric=parsed.value_numeric,
            unit=unit,
            reference_low=parsed.reference_low,
            reference_high=parsed.reference_high,
            reference_text=reference_text,
            flag=parsed.flag,
            bbox_left=parsed.bbox_left,
            bbox_top=parsed.bbox_top,
            bbox_right=parsed.bbox_right,
            bbox_bottom=parsed.bbox_bottom,
            ocr_confidence=parsed.ocr_confidence,
            review_status=0,
            source_file=report.file_name,
            source_path=report.storage_path,
        )
        self.db.add(result)

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """解析日期字符串

        支持多种格式，包括 OCR 输出中日期与时间无分隔的情况（如 2026-01-0708:23:58）。
        """
        if not date_str:
            return None
        # 尝试在日期和时间之间补空格：YYYY-MM-DD 紧跟 HH:MM
        import re
        normalized = re.sub(
            r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})(\d{1,2}:\d{1,2})",
            r"\1 \2",
            date_str.strip(),
        )
        for fmt in [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d",
        ]:
            try:
                return datetime.strptime(normalized, fmt)
            except ValueError:
                continue
        return None
