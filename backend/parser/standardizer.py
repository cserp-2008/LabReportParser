"""指标标准化服务

将不同医院/报告中的指标别名统一映射到标准检验项目。
依据设计说明书 2.1.4 检验指标标准化需求。
"""
import re
from typing import Optional, Dict, List
from sqlalchemy.orm import Session

from db.models import LabItem, Alias


class Standardizer:
    """指标标准化器"""

    def __init__(self, db: Session):
        self.db = db
        self._alias_map: Optional[Dict[str, int]] = None
        self._item_map: Optional[Dict[str, LabItem]] = None

    def _load_mappings(self):
        """加载别名映射表（惰性加载）"""
        if self._alias_map is not None:
            return

        self._alias_map = {}
        aliases = self.db.query(Alias).all()
        for alias in aliases:
            # 别名小写做匹配
            self._alias_map[alias.alias_name.lower()] = alias.item_id

        # 同时将标准名本身也加入映射
        items = self.db.query(LabItem).all()
        self._item_map = {}
        for item in items:
            self._item_map[item.item_id] = item
            if item.item_name:
                self._alias_map[item.item_name.lower()] = item.item_id
            if item.abbr:
                self._alias_map[item.abbr.lower()] = item.item_id

    def standardize(self, raw_name: str, code: str = "") -> Optional[LabItem]:
        """将原始指标名映射到标准检验项目

        Args:
            raw_name: 原始提取的指标名称
            code: 化验单上的英文简称（如ALT、AST），用于匹配标准指标库的缩写

        Returns:
            匹配到的标准检验项目，未匹配返回 None
        """
        self._load_mappings()

        if code:
            code_normalized = code.strip().lower()
            item_id = self._alias_map.get(code_normalized)
            if item_id and self._item_map:
                return self._item_map[item_id]

        if not raw_name:
            return None

        normalized = raw_name.strip().lower()

        item_id = self._alias_map.get(normalized)
        if item_id and self._item_map:
            return self._item_map[item_id]

        cleaned = self._clean_name(raw_name)
        if cleaned != normalized:
            item_id = self._alias_map.get(cleaned)
            if item_id and self._item_map:
                return self._item_map[item_id]

        for alias_key, iid in self._alias_map.items():
            if alias_key and (alias_key in normalized or normalized in alias_key):
                if len(alias_key) >= 2:
                    return self._item_map.get(iid)

        return None

    def _clean_name(self, name: str) -> str:
        """清理指标名，去除常见干扰字符"""
        cleaned = name.strip()
        
        cleaned = cleaned.replace("*", "")
        cleaned = cleaned.replace("△", "")
        cleaned = cleaned.replace("＊", "")
        
        cleaned = re.sub(r"[（\(]干化学法[）\)]", "", cleaned)
        cleaned = re.sub(r"[（\(][^）\)]+[）\)]", "", cleaned)
        
        cleaned = re.sub(r"^\d+\s*", "", cleaned)
        cleaned = re.sub(r"^\[\d+", "", cleaned)
        
        cleaned = re.sub(r"^[A-Z][A-Za-z0-9/\-._]*\s*[%#]?\s*", "", cleaned)
        cleaned = re.sub(r"^[A-Za-z0-9/\-._]+\s+[*△＊]?\s*", "", cleaned)
        cleaned = re.sub(r"^[A-Za-z0-9/\-._]+[\s]*[*△＊]+\s*", "", cleaned)
        
        cleaned = re.sub(r"^-\s*", "", cleaned)
        cleaned = re.sub(r"^eGFR\s*", "", cleaned)
        cleaned = re.sub(r"^CMV-DNA\s*", "", cleaned)
        cleaned = re.sub(r"^EB-?DNA\s*", "", cleaned)
        cleaned = re.sub(r"^EB病毒\s*", "", cleaned)
        cleaned = re.sub(r"^COBAS\s*", "", cleaned)
        cleaned = re.sub(r"^D-Dime\s*", "", cleaned)
        cleaned = re.sub(r"^PCR\s*", "", cleaned)
        cleaned = re.sub(r"^typing\s+[a-zA-Z]+\s*", "", cleaned)
        cleaned = re.sub(r"^Phagocyte-ST\s*", "", cleaned)
        cleaned = re.sub(r"^PIVKA-\s*", "", cleaned)
        cleaned = re.sub(r"^MALB(?:/[a-zA-Z]+)?\s*", "", cleaned)
        cleaned = re.sub(r"^u-TP(?:/[a-zA-Z]+)?\s*", "", cleaned)
        cleaned = re.sub(r"^hs-[a-zA-Z]+\s*", "", cleaned)
        cleaned = re.sub(r"^hs[CR]+\s*", "", cleaned)
        cleaned = re.sub(r"^TPOAB\s*", "", cleaned)
        cleaned = re.sub(r"^TNF-\s*", "", cleaned)
        cleaned = re.sub(r"^TSH\s*\*\s*", "", cleaned)
        cleaned = re.sub(r"^UCREA\s*", "", cleaned)
        cleaned = re.sub(r"^UCB\s*", "", cleaned)
        cleaned = re.sub(r"^NEUT%\s*", "", cleaned)
        cleaned = re.sub(r"^LYMPH%\s*", "", cleaned)
        cleaned = re.sub(r"^EO#\s*", "", cleaned)
        cleaned = re.sub(r"^N端-前脑钠肽\s*", "", cleaned)
        cleaned = re.sub(r"^C-Ca\s*", "", cleaned)
        cleaned = re.sub(r"^-3-β-D-\s*", "", cleaned)
        cleaned = re.sub(r"^Y-\s*", "", cleaned)
        cleaned = re.sub(r"^Ca\s*", "", cleaned)
        
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        
        cleaned = cleaned.rstrip("0123456789. ")
        return cleaned.lower()
