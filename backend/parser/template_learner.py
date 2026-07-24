"""医院模板学习服务

人工复核时自动学习报告特征：
- 指标名称映射（raw_item_name → 标准化名称）
- 单位修正
- 参考区间格式
- 异常标记规则
"""
import json
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from db.models import Hospital, LabResult, Report

logger = logging.getLogger(__name__)


class TemplateLearner:
    """医院模板学习器"""

    def __init__(self, db: Session):
        self.db = db

    def learn_from_review(
        self,
        result: LabResult,
        old_values: Optional[Dict] = None,
    ) -> bool:
        """从人工复核中学习报告特征

        当用户修改了检验结果时，自动将修改记录到医院模板中。

        Args:
            result: 修改后的 LabResult 对象
            old_values: 修改前的值 dict

        Returns:
            是否更新了模板
        """
        report = self.db.query(Report).filter(
            Report.report_id == result.report_id
        ).first()
        if not report or not report.hospital_id:
            return False

        hospital = self.db.query(Hospital).filter(
            Hospital.hospital_id == report.hospital_id
        ).first()
        if not hospital:
            return False

        # 加载现有模板配置
        template = self._load_template(hospital)

        # 学习指标名称映射
        updated = self._learn_item_mapping(template, result, old_values)

        # 学习单位
        updated = self._learn_unit(template, result) or updated

        # 学习参考区间格式
        updated = self._learn_reference_format(template, result) or updated

        if updated:
            self._save_template(hospital, template)
            logger.info(
                f"医院模板已更新: hospital_id={hospital.hospital_id}, "
                f"result_id={result.result_id}"
            )

        return updated

    def _load_template(self, hospital: Hospital) -> Dict[str, Any]:
        """加载医院模板配置"""
        if hospital.template_config:
            try:
                return json.loads(hospital.template_config)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "item_mappings": {},
            "unit_mappings": {},
            "reference_formats": {},
            "learn_count": 0,
        }

    def _save_template(self, hospital: Hospital, template: Dict[str, Any]):
        """保存模板配置"""
        template["learn_count"] = template.get("learn_count", 0) + 1
        template["last_updated"] = str(__import__("datetime").datetime.now())
        hospital.template_config = json.dumps(template, ensure_ascii=False, indent=2)

    def _learn_item_mapping(
        self,
        template: Dict,
        result: LabResult,
        old_values: Optional[Dict],
    ) -> bool:
        """学习指标名称映射: old_raw_item_name → new_raw_item_name"""
        if not result.raw_item_name:
            return False

        if old_values and old_values.get("raw_item_name"):
            mappings = template.setdefault("item_mappings", {})
            old_raw_name = old_values["raw_item_name"].strip()
            new_raw_name = result.raw_item_name.strip()

            if old_raw_name != new_raw_name:
                mappings[old_raw_name] = new_raw_name
                return True

        return False

    def _learn_unit(self, template: Dict, result: LabResult) -> bool:
        """学习单位映射"""
        if not result.raw_item_name or not result.unit:
            return False

        unit_mappings = template.setdefault("unit_mappings", {})
        raw_name = result.raw_item_name.strip()
        unit = result.unit.strip()

        existing = unit_mappings.get(raw_name)
        if existing != unit:
            unit_mappings[raw_name] = unit
            return True

        return False

    def _learn_reference_format(self, template: Dict, result: LabResult) -> bool:
        """学习参考区间格式"""
        if not result.raw_item_name or not result.reference_text:
            return False

        ref_formats = template.setdefault("reference_formats", {})
        raw_name = result.raw_item_name.strip()
        ref_text = result.reference_text.strip()

        existing = ref_formats.get(raw_name)
        if existing != ref_text:
            ref_formats[raw_name] = ref_text
            return True

        return False

    def get_template(self, hospital_id: int) -> Optional[Dict[str, Any]]:
        """获取医院模板配置"""
        hospital = self.db.query(Hospital).filter(
            Hospital.hospital_id == hospital_id
        ).first()
        if not hospital:
            return None

        return self._load_template(hospital)

    def clear_template(self, hospital_id: int) -> bool:
        """清除医院模板学习特征"""
        hospital = self.db.query(Hospital).filter(
            Hospital.hospital_id == hospital_id
        ).first()
        if not hospital:
            return False

        hospital.template_config = None
        self.db.commit()
        return True

    def apply_template(
        self,
        hospital_id: Optional[int],
        raw_item_name: str,
    ) -> Dict[str, str]:
        """应用医院模板规则，返回修正后的指标信息

        Args:
            hospital_id: 医院ID
            raw_item_name: 原始指标名称

        Returns:
            dict with keys: item_name, unit, reference_text
        """
        result = {"item_name": None, "unit": None, "reference_text": None}

        if not hospital_id or not raw_item_name:
            return result

        template = self.get_template(hospital_id)
        if not template:
            return result

        raw_name = raw_item_name.strip()

        # 应用指标名称映射
        item_mappings = template.get("item_mappings", {})
        if raw_name in item_mappings:
            result["item_name"] = item_mappings[raw_name]

        # 应用单位映射
        unit_mappings = template.get("unit_mappings", {})
        if raw_name in unit_mappings:
            result["unit"] = unit_mappings[raw_name]

        # 应用参考区间格式
        ref_formats = template.get("reference_formats", {})
        if raw_name in ref_formats:
            result["reference_text"] = ref_formats[raw_name]

        return result
