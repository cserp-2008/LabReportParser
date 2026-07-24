"""南京明基医院专用解析器

基于OCR坐标数据进行精准解析，支持单栏和双栏布局。

报告特征（852x1100分辨率，OCR后约1550宽度）：
1. 医院标识：南京明基医院、南京医科大学附属明基医院
2. 双栏布局（生化全套）：左栏x=140-750，右栏x=830-1500
3. 单栏布局（免疫类）：各列位置固定
4. 表头字段：代号、项目名称、结果、提示、单位、参考范围
"""
import re
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field

from .lab_result_parser import ParsedResult, ParsedReport


@dataclass
class OCRItem:
    """OCR识别结果"""
    text: str
    x: float
    y: float
    width: float
    height: float
    conf: float


@dataclass
class NBMCItem:
    """南京明基医院检验项目"""
    code: str
    name: str
    result: str
    unit: str
    ref_range: str
    flag: Optional[str] = None


class NBMCParser:
    """南京明基医院专用解析器"""

    HOSPITAL_NAMES = ["南京明基医院", "南京医科大学附属明基医院"]

    PATIENT_PATTERNS = {
        "name": [
            r"姓名[:：]\s*([\u4e00-\u9fa5]{2,4})",
            r"姓\s*名\s*([\u4e00-\u9fa5]{2,4})",
        ],
        "gender": [
            r"性别[:：]\s*([男女])",
            r"性\s*别\s*([男女])",
        ],
        "age": [
            r"年龄[:：]\s*(\d{1,3})\s*岁?",
            r"年\s*龄\s*(\d{1,3})\s*岁?",
        ],
        "sample_time": [
            r"采样时间[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
            r"采样时间[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        ],
        "report_time": [
            r"报告时间[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
            r"报告时间[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        ],
    }

    def parse(self, text: str, page_no: int = 1) -> ParsedReport:
        """解析南京明基医院报告"""
        report = ParsedReport()

        if not text:
            return report

        report.hospital_name = "南京明基医院"

        report.patient_name = self._extract(text, "name")
        report.gender = self._extract(text, "gender")
        report.age = self._extract(text, "age")
        report.sample_time = self._extract(text, "sample_time")
        report.report_time = self._extract(text, "report_time")

        ocr_items = self._parse_ocr_text(text)
        if not ocr_items:
            return report

        items = self._parse_table_from_coords(ocr_items)

        report.results = self._convert_to_parsed_results(items, page_no)
        report.quality_score = self._calculate_quality_score(report)

        return report

    def _extract(self, text: str, field: str) -> Optional[str]:
        patterns = self.PATIENT_PATTERNS.get(field, [])
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def _parse_ocr_text(self, text: str) -> List[OCRItem]:
        """解析OCR文本，提取坐标信息"""
        items = []
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            match = re.match(
                r"\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*x\s*([\d.]+)\s*\)\s*conf=([\d.]+)\s*text=(.+)",
                line
            )
            if match:
                items.append(OCRItem(
                    x=float(match.group(1)),
                    y=float(match.group(2)),
                    width=float(match.group(3)),
                    height=float(match.group(4)),
                    conf=float(match.group(5)),
                    text=match.group(6).strip().strip("'\""),
                ))
        return items

    def _parse_table_from_coords(self, ocr_items: List[OCRItem]) -> List[NBMCItem]:
        """基于坐标解析表格"""
        if not ocr_items:
            return []

        header_items = [i for i in ocr_items if self._is_header_text(i.text)]
        if not header_items:
            return self._parse_fallback(ocr_items)

        layout = self._detect_layout(header_items, ocr_items)
        if layout == "double":
            return self._parse_double_column_coords(ocr_items)
        else:
            return self._parse_single_column_coords(ocr_items)

    def _is_header_text(self, text: str) -> bool:
        """判断是否为表头文本"""
        headers = ["代号", "项目名称", "结果", "提示", "单位", "参考范围", "参考区间"]
        if len(text) > 30:
            return False
        if "前注" in text or "本次实验" in text:
            return False
        return any(h in text for h in headers)

    def _detect_layout(self, header_items: List[OCRItem], all_items: List[OCRItem]) -> str:
        """检测布局类型
        
        单栏：表头列数较少，无重复列名
        双栏：有两套相同的列名，右栏有独立的表头
        """
        if not header_items:
            return "single"

        header_counts = {}
        for item in header_items:
            for h in ["代号", "项目名称", "结果", "单位", "参考范围"]:
                if h in item.text:
                    header_counts[h] = header_counts.get(h, 0) + 1
        
        if any(count >= 2 for count in header_counts.values()):
            return "double"

        header_y_max = max(i.y for i in header_items)
        data_items = [i for i in all_items if i.y > header_y_max and i.y < header_y_max + 500]
        if data_items:
            max_x = max(i.x for i in data_items)
            if max_x > 1400:
                return "double"
        
        return "single"

    def _parse_single_column_coords(self, ocr_items: List[OCRItem]) -> List[NBMCItem]:
        """解析单栏布局（免疫类报告）
        
        实际坐标范围（基于OCR数据）：
        - 代号: x < 200
        - 项目名称: 200 < x < 680
        - 结果: 680 < x < 850
        - 提示: 850 < x < 950
        - 单位: 950 < x < 1100
        - 参考范围: 1100 < x < 1500
        """
        items = []

        header_items = [i for i in ocr_items if self._is_header_text(i.text)]
        if not header_items:
            return items

        min_y = max(i.y for i in header_items) + 15
        footer_y = self._find_footer_y(ocr_items)

        data_items = [i for i in ocr_items if min_y < i.y < footer_y and not self._is_header_text(i.text)]
        rows = self._group_by_row(data_items)

        for row in rows:
            item = NBMCItem(code="", name="", result="", unit="", ref_range="")
            for i in row:
                if i.x < 200:
                    if re.match(r"^[A-Z0-9\-]+$", i.text):
                        item.code = i.text
                    else:
                        item.name += i.text
                elif i.x < 680:
                    item.name += i.text
                elif i.x < 850:
                    item.result += i.text
                elif i.x < 900:
                    pass
                elif i.x < 1100:
                    item.unit += i.text
                else:
                    item.ref_range += i.text

            self._clean_item(item)

            if item.name and item.result and self._is_valid_result(item.result):
                items.append(item)

        return items

    def _parse_double_column_coords(self, ocr_items: List[OCRItem]) -> List[NBMCItem]:
        """解析双栏布局（生化全套）
        
        实际坐标范围（基于OCR数据，页面宽度约1550）：
        左栏（x < 800）：
        - 代号/项目: x < 420
        - 结果: 420 < x < 560
        - 单位/参考: 560 < x < 800
        
        右栏（x >= 800）：
        - 代号/项目: 800 < x < 1120
        - 结果: 1120 < x < 1250
        - 单位/参考: 1250 < x < 1550
        """
        items = []

        header_items = [i for i in ocr_items if self._is_header_text(i.text)]
        if not header_items:
            return items

        min_y = max(i.y for i in header_items) + 15
        footer_y = self._find_footer_y(ocr_items)

        data_items = [i for i in ocr_items if min_y < i.y < footer_y and not self._is_header_text(i.text)]
        rows = self._group_by_row(data_items)

        for row in rows:
            left_item = NBMCItem(code="", name="", result="", unit="", ref_range="")
            right_item = NBMCItem(code="", name="", result="", unit="", ref_range="")

            for i in row:
                if i.x < 800:
                    if i.x < 420:
                        text = i.text
                        if '*' in text:
                            parts = text.split('*', 1)
                            if len(parts) == 2:
                                code_part = parts[0].strip()
                                name_part = parts[1].strip()
                                if re.match(r"^[A-Z0-9\-]+$", code_part):
                                    left_item.code = code_part
                                else:
                                    left_item.name += code_part
                                left_item.name += name_part
                        elif re.match(r"^[A-Z0-9#%/\-\.]+$", text) and len(text) <= 15:
                            left_item.code = text
                        else:
                            # 尝试拆分无 * 分隔的"代号+名称(+结果)"合并文本
                            code, name, result = self._split_merged_code_name(text)
                            if code and name:
                                left_item.code = code
                                left_item.name += name
                                if result:
                                    left_item.result += result
                            else:
                                left_item.name += text
                    elif i.x < 560:
                        left_item.result += i.text
                    else:
                        self._assign_unit_ref(i.text, left_item)
                else:
                    if i.x < 1100:
                        text = i.text
                        if '*' in text:
                            parts = text.split('*', 1)
                            if len(parts) == 2:
                                code_part = parts[0].strip()
                                name_part = parts[1].strip()
                                if re.match(r"^[A-Z0-9\-]+$", code_part):
                                    right_item.code = code_part
                                else:
                                    right_item.name += code_part
                                right_item.name += name_part
                        elif re.match(r"^[A-Z0-9#%/\-\.]+$", text) and len(text) <= 15:
                            right_item.code = text
                        else:
                            # 尝试拆分无 * 分隔的"代号+名称(+结果)"合并文本
                            code, name, result = self._split_merged_code_name(text)
                            if code and name:
                                right_item.code = code
                                right_item.name += name
                                if result:
                                    right_item.result += result
                            else:
                                right_item.name += text
                    elif i.x < 1250:
                        right_item.result += i.text
                    else:
                        self._assign_unit_ref(i.text, right_item)

            self._clean_item(left_item)
            self._clean_item(right_item)

            if left_item.name and left_item.result and self._is_valid_result(left_item.result):
                items.append(left_item)

            if right_item.name and right_item.result and self._is_valid_result(right_item.result):
                items.append(right_item)

        return items

    # 右栏无 * 分隔的"代号+名称(+结果)"合并文本拆分正则
    _MERGE_SPLIT_PATTERN = re.compile(
        r"^(?P<code>[A-Z][A-Za-z0-9#%/\-\.]{0,8})"
        r"(?P<name>[\u4e00-\u9fa5（）\(\)/＋\-]+)"
        r"(?P<result>[\d\.].*)?$"
    )

    # 代号 OCR 误识修正
    _CODE_OCR_FIXES = {
        "BAS0%": "BAS%", "BA0%": "BA%", "EO0%": "EO%",
        "NEUT0%": "NEUT%", "LYM0%": "LYM%", "MON0%": "MON%",
    }

    def _split_merged_code_name(self, text: str) -> Tuple[str, str, str]:
        """拆分右栏无 * 分隔符的合并文本。

        示例：
            "NEUT#中性粒细胞计数"      -> ("NEUT#", "中性粒细胞计数", "")
            "BAS0%嗜碱性粒细胞百分比0.1" -> ("BAS%", "嗜碱性粒细胞百分比", "0.1")
            "PCT血小板压积0.25"        -> ("PCT", "血小板压积", "0.25")

        Returns: (code, name, result) 其中 code/result 可能为空字符串
        """
        m = self._MERGE_SPLIT_PATTERN.match(text.strip())
        if not m:
            return "", text, ""
        code = m.group("code") or ""
        name = m.group("name") or ""
        result = (m.group("result") or "").strip()
        # 代号 OCR 修正
        code = self._CODE_OCR_FIXES.get(code, code)
        return code, name, result

    def _parse_unit_ref(self, text: str, item: NBMCItem):
        """解析单位和参考范围的组合文本
        
        处理格式：
        - "11--16" -> 只有参考范围
        - "umol/L 0--19" -> 单位 + 参考范围
        - "1. 04-2. 02" -> 参考范围（注意可能有空格）
        - "g/L" -> 只有单位
        """
        text = text.strip()
        
        text_clean = text.replace(" ", "")
        ref_pattern = r"(\d+\.?\d*)\s*[-~—–]+\s*(\d+\.?\d*)"
        ref_match = re.search(ref_pattern, text_clean)
        
        if ref_match:
            ref_low = ref_match.group(1)
            ref_high = ref_match.group(2)
            ref_range = f"{ref_low}-{ref_high}"
            if ref_range:
                item.ref_range = ref_range
            
            unit_part = ""
            for unit in ['umol/L', 'U/L', 'mmol/L', 'g/L', 'ml/min', '%']:
                if unit in text:
                    unit_part = unit
                    break
            if unit_part and not item.unit:
                item.unit = unit_part
        elif "<" in text or "≤" in text or ">" in text or "≥" in text:
            if not item.ref_range:
                item.ref_range = text
        else:
            if not item.unit:
                item.unit = text

    def _assign_unit_ref(self, text: str, item: NBMCItem):
        """根据内容判断是单位还是参考范围"""
        text = text.strip()

        # 先处理 "10~9/L 0.00--0.06" 这种"单位+空格+参考范围"的合并文本
        unit_prefix_pattern = re.compile(r"^(10[\^~'”*\s]*\d+\s*/\s*L)\s+(.+)$")
        m = unit_prefix_pattern.match(text)
        if m:
            unit_part = m.group(1).replace(" ", "")
            rest = m.group(2).strip()
            # 规范化单位
            unit_part = self._normalize_unit(unit_part)
            if not item.unit:
                item.unit = unit_part
            # 处理剩余的参考范围
            if rest:
                self._assign_unit_ref(rest, item)
            return

        unit_patterns = ['umol/L', 'U/L', 'mmol/L', 'g/L', 'ml/min', '%', 'pg', 'ng/ml', 'mg/L']

        # 参考范围模式：支持带空格的数字（如 "1. 80--6. 30"）
        ref_pattern = r"(\d+\.?\d*(?:\s+\d+)?)\s*[-–]+\s*(\d+\.?\d*(?:\s+\d+)?)"

        if any(u in text for u in unit_patterns):
            if re.search(ref_pattern, text):
                self._parse_unit_ref(text, item)
            else:
                item.unit += text
        elif re.search(ref_pattern, text):
            ref_match = re.search(ref_pattern, text)
            ref_low = ref_match.group(1).replace(" ", "")
            ref_high = ref_match.group(2).replace(" ", "")
            item.ref_range = f"{ref_low}-{ref_high}"
        elif '<' in text or '≤' in text or '>' in text or '≥' in text:
            item.ref_range += text
        else:
            if not item.unit:
                item.unit += text

    def _clean_item(self, item: NBMCItem):
        """后处理清理项目：
        1. 拆分包含 '*' 的名称（代码+名称合并的情况）
        2. 去除结果中的空格
        3. 去除名称开头的 '*'
        4. 清理参考范围中的多余空格
        5. 从单位中提取参考范围（处理单位和参考范围合并的情况）
        6. 去除名称中的(干化学法)和前缀字母/符号
        """
        item.name = item.name.strip()
        item.result = item.result.strip().replace(" ", "")
        item.unit = item.unit.strip()
        item.ref_range = item.ref_range.strip().replace(" ", "")

        if '*' in item.name:
            parts = item.name.split('*', 1)
            if len(parts) == 2:
                prefix = parts[0].strip()
                suffix = parts[1].strip()
                if re.match(r"^[A-Z0-9\-]+$", prefix) and not item.code:
                    item.code = prefix
                    item.name = suffix
                else:
                    item.name = suffix

        if item.name.startswith("*"):
            item.name = item.name[1:].strip()

        item.name = item.name.replace("△", "")
        item.name = item.name.replace("＊", "")
        
        item.name = re.sub(r"[（\(]干化学法[）\)]", "", item.name)
        item.name = re.sub(r"[（\(][^）\)]+[）\)]", "", item.name)
        
        item.name = re.sub(r"^\d+\s*", "", item.name)
        item.name = re.sub(r"^\[\d+", "", item.name)
        
        item.name = re.sub(r"^[A-Z][A-Za-z0-9/\-._]*\s*[%#]?\s*", "", item.name)
        item.name = re.sub(r"^[A-Za-z0-9/\-._]+\s+[*△＊]?\s*", "", item.name)
        item.name = re.sub(r"^[A-Za-z0-9/\-._]+[\s]*[*△＊]+\s*", "", item.name)
        
        item.name = re.sub(r"^-\s*", "", item.name)
        item.name = re.sub(r"^eGFR\s*", "", item.name)
        item.name = re.sub(r"^CMV-DNA\s*", "", item.name)
        item.name = re.sub(r"^EB-?DNA\s*", "", item.name)
        item.name = re.sub(r"^EB病毒\s*", "", item.name)
        item.name = re.sub(r"^COBAS\s*", "", item.name)
        item.name = re.sub(r"^D-Dime\s*", "", item.name)
        item.name = re.sub(r"^PCR\s*", "", item.name)
        item.name = re.sub(r"^typing\s+[a-zA-Z]+\s*", "", item.name)
        item.name = re.sub(r"^Phagocyte-ST\s*", "", item.name)
        item.name = re.sub(r"^PIVKA-\s*", "", item.name)
        item.name = re.sub(r"^MALB(?:/[a-zA-Z]+)?\s*", "", item.name)
        item.name = re.sub(r"^u-TP(?:/[a-zA-Z]+)?\s*", "", item.name)
        item.name = re.sub(r"^hs-[a-zA-Z]+\s*", "", item.name)
        item.name = re.sub(r"^hs[CR]+\s*", "", item.name)
        item.name = re.sub(r"^TPOAB\s*", "", item.name)
        item.name = re.sub(r"^TNF-\s*", "", item.name)
        item.name = re.sub(r"^TSH\s*\*\s*", "", item.name)
        item.name = re.sub(r"^UCREA\s*", "", item.name)
        item.name = re.sub(r"^UCB\s*", "", item.name)
        item.name = re.sub(r"^NEUT%\s*", "", item.name)
        item.name = re.sub(r"^LYMPH%\s*", "", item.name)
        item.name = re.sub(r"^EO#\s*", "", item.name)
        item.name = re.sub(r"^N端-前脑钠肽\s*", "", item.name)
        item.name = re.sub(r"^C-Ca\s*", "", item.name)
        item.name = re.sub(r"^-3-β-D-\s*", "", item.name)
        item.name = re.sub(r"^Y-\s*", "", item.name)
        item.name = re.sub(r"^Ca\s*", "", item.name)
        
        item.name = re.sub(r"^>\s*[\d.]+\s*", "", item.name)
        item.name = re.sub(r"^<\s*[\d.]+\s*", "", item.name)
        
        if re.match(r"^α-羟丁酸脱氢酶\s+[\d]", item.name):
            item.name = "α-羟丁酸脱氢酶"
        elif re.match(r"^β2微球蛋白\s+[\d]", item.name):
            item.name = "β2微球蛋白"
        
        item.name = re.sub(r"\s+", " ", item.name).strip()

        if item.unit and not item.ref_range:
            text_clean = item.unit.replace(" ", "")
            ref_pattern = r"(\d+\.?\d*)\s*[-~—–]\s*(\d+\.?\d*)"
            ref_match = re.search(ref_pattern, text_clean)
            
            units = ['umol/L', 'U/L', 'mmol/L', 'g/L', 'ml/min', '%']
            found_unit = ""
            for u in units:
                if u in item.unit:
                    found_unit = u
                    break
            
            if ref_match:
                ref_low = ref_match.group(1)
                ref_high = ref_match.group(2)
                item.ref_range = f"{ref_low}-{ref_high}"
                item.unit = found_unit
            elif '<' in item.unit or '≤' in item.unit or '>' in item.unit or '≥' in item.unit:
                item.ref_range = item.unit
                item.unit = found_unit
            else:
                for u in units:
                    if u in item.unit:
                        item.unit = u
                        break

        if item.ref_range:
            item.ref_range = item.ref_range.replace(" ", "")
            
        if item.ref_range and item.unit:
            for u in ['umol/L', 'U/L', 'mmol/L', 'g/L', 'ml/min', '%']:
                if u in item.ref_range:
                    item.ref_range = item.ref_range.replace(u, "").strip()
        
        if item.unit:
            text_clean = item.unit.replace(" ", "")
            ref_pattern = r"(\d+\.?\d*)\s*[-~—–]\s*(\d+\.?\d*)"
            ref_match = re.search(ref_pattern, text_clean)
            if ref_match and not item.ref_range:
                ref_low = ref_match.group(1)
                ref_high = ref_match.group(2)
                item.ref_range = f"{ref_low}-{ref_high}"
                units = ['umol/L', 'U/L', 'mmol/L', 'g/L', 'ml/min', '%']
                found_unit = ""
                for u in units:
                    if u in item.unit:
                        found_unit = u
                        break
                item.unit = found_unit

        if item.unit and ('<' in item.unit or '≤' in item.unit or '>' in item.unit or '≥' in item.unit):
            if not item.ref_range:
                item.ref_range = item.unit
                item.unit = ""

        if item.ref_range:
            item.ref_range = item.ref_range.replace(" ", "")

        # 单位 OCR 纠正（TJ→fL, 10~9/L→10^9/L 等）
        item.unit = self._normalize_unit(item.unit)

    # 非数值结果白名单（血型/阴阳性质等）
    _NON_NUMERIC_RESULTS = {
        "A", "B", "O", "AB", "A型", "B型", "O型", "AB型",
        "阳性", "阴性", "弱阳性", "弱阴性", "可疑",
        "+", "-", "++", "+++", "±", "阳性(+)", "阴性(-)",
        "CcEe", "CcEE", "CCee", "CCEE", "ccEe", "ccEE", "ccEE",
        "未凝集", "凝集", "无菌生长", "培养阴性", "培养阳性",
        "未见异常", "正常",
    }

    _NON_NUMERIC_PATTERNS = [
        re.compile(r"^[A-Za-z0-9\+\-±]+$"),
        re.compile(r"^(?:阳性|阴性|弱阳性|弱阴性|可疑)(?:\([+\-]\))?$"),
        re.compile(r"^\d+\s*[:：]\s*\d+$"),
        re.compile(r"^[A-Za-z]+(?:阳性|阴性)$"),
        re.compile(r"^[\u4e00-\u9fa5]{2,8}$"),
    ]

    def _is_valid_result(self, result: str) -> bool:
        """检查结果是否有效（支持数值和非数值结果）"""
        result_clean = result.strip().replace(" ", "")
        if not result_clean:
            return False
        # 数值结果
        try:
            val = float(result_clean)
            return -10000 <= val <= 100000
        except ValueError:
            pass
        # 非数值结果白名单
        if result_clean in self._NON_NUMERIC_RESULTS:
            return True
        # 模式匹配
        for pat in self._NON_NUMERIC_PATTERNS:
            if pat.match(result_clean):
                return True
        return False

    # 单位 OCR 误识修正映射表
    _UNIT_OCR_FIXES = {
        "TJ": "fL", "Tj": "fL", "tj": "fL", "FL": "fL",
        "10~9/L": "10^9/L", "10”9/L": "10^9/L", "10'9/L": "10^9/L",
        "10*9/L": "10^9/L", "109/L": "10^9/L",
        "10~12/L": "10^12/L", "10”12/L": "10^12/L", "10*12/L": "10^12/L",
        "molL": "mol/L", "mmoIL": "mmol/L", "umolL": "umol/L",
    }

    _UNIT_REGEX_FIXES = [
        (re.compile(r"10[\^~'”*\s]*9\s*/\s*L"), "10^9/L"),
        (re.compile(r"10[\^~'”*\s]*12\s*/\s*L"), "10^12/L"),
    ]

    def _normalize_unit(self, unit: str) -> str:
        """规范化单位字段，修正 OCR 错误"""
        if not unit:
            return unit
        u = unit.strip().replace(" ", "")
        if u in self._UNIT_OCR_FIXES:
            return self._UNIT_OCR_FIXES[u]
        for pat, repl in self._UNIT_REGEX_FIXES:
            u = pat.sub(repl, u)
        return u

    def _find_footer_y(self, ocr_items: List[OCRItem]) -> float:
        footer_keywords = ["备注", "注：", "申请医生", "报告时间", "检验者", "审核者", "本次实验", "项目名称前注"]
        footer_y = max(i.y for i in ocr_items)
        
        for i in ocr_items:
            for kw in footer_keywords:
                if kw in i.text:
                    footer_y = min(footer_y, i.y)
        
        return footer_y

    def _group_by_row(self, items: List[OCRItem], y_threshold: float = 18.0) -> List[List[OCRItem]]:
        """按Y坐标分组为行

        改进：使用行内中位数y作为比较基准，避免长行漂移；
        当行内已有≥3项时收紧阈值到0.8倍，防止相邻行误并。
        """
        if not items:
            return []

        items.sort(key=lambda i: i.y)
        rows = []
        current_row = [items[0]]

        for i in items[1:]:
            ys = sorted(it.y for it in current_row)
            med = ys[len(ys) // 2]
            effective_thresh = y_threshold if len(current_row) < 3 else y_threshold * 0.8
            if abs(i.y - med) <= effective_thresh:
                current_row.append(i)
            else:
                current_row.sort(key=lambda x: x.x)
                rows.append(current_row)
                current_row = [i]

        if current_row:
            current_row.sort(key=lambda x: x.x)
            rows.append(current_row)

        return rows

    def _parse_fallback(self, ocr_items: List[OCRItem]) -> List[NBMCItem]:
        """回退解析：按行文本解析"""
        items = []
        rows = self._group_by_row(ocr_items)

        for row in rows:
            line_text = " ".join(i.text for i in row)
            if not line_text or len(line_text) < 5:
                continue

            if self._is_header_text(line_text):
                continue

            item = self._parse_line_text(line_text)
            if item:
                items.append(item)

        return items

    def _parse_line_text(self, line: str) -> Optional[NBMCItem]:
        """解析单行文本"""
        line = line.replace("  ", " ")
        parts = line.split()
        if len(parts) < 3:
            return None

        code = ""
        name = ""
        result = ""
        unit = ""
        ref_range = ""

        ref_match = re.search(r"([\d.]+)\s*[-~]\s*([\d.]+)", line)
        if ref_match:
            ref_range = ref_match.group(0)
            before_ref = line[:ref_match.start()].strip()
            parts_before = before_ref.split()

            if len(parts_before) >= 2:
                result = parts_before[-1]
                if re.match(r"^[\d.]+$", result):
                    if len(parts_before) >= 3:
                        unit = parts_before[-2]
                        remaining = " ".join(parts_before[:-2])
                    else:
                        unit = ""
                        remaining = " ".join(parts_before[:-1])

                    code_match = re.match(r"^([A-Za-z0-9\-]+)\s*", remaining)
                    if code_match:
                        code = code_match.group(1)
                        name = remaining[len(code):].strip()
                    else:
                        name = remaining

        if not name or not result:
            return None

        if not re.match(r"^[\d.]+$", result):
            return None

        if float(result) > 100000 or float(result) < -10000:
            return None

        return NBMCItem(code=code, name=name, result=result, unit=unit, ref_range=ref_range)

    def _is_invalid_item(self, name: str) -> bool:
        """判断是否为无效条目"""
        invalid_keywords = [
            "申请医师",
            "检验者",
            "审核者",
            "第1页",
            "页/共",
            "备注",
            "注：",
            "采集时间",
            "报告时间",
            "接收时间",
            "检验备注",
            "样本号",
            "条码号",
            "地址：",
            "检测结果可能受",
            "具体数值：",
            "鉴定结果：",
            "送检医生",
            "送检科室",
            "病区",
            "床号",
            "姓名",
            "性别",
            "年龄",
            "住院号",
            "门诊号",
            "科室",
            "标本号",
            "检测方法",
            "检测仪器",
            "样本类型",
            "样本状态",
            "送检时间",
            "审核时间",
            "打印时间",
            "报告日期",
            "女：晨尿：",
            "附见：",
            "腹腔内见",
            "荧光定量PCR",
            "王敏",
            "PCR",
        ]
        for keyword in invalid_keywords:
            if keyword in name:
                return True
        
        if not name:
            return True
        
        if name.startswith("(cid:"):
            return True
        
        if name in ["≤", "≥", "/", "α", "β"]:
            return True
        
        if len(name) > 50:
            return True
        
        if re.match(r"^[<>]?\s*[\d.]+\s*$", name):
            return True
        
        if re.match(r"^[αβγδθλμνπσφψω]$", name):
            return True
        
        return False

    def _convert_to_parsed_results(self, items: List[NBMCItem], page_no: int) -> List[ParsedResult]:
        """转换为标准 ParsedResult 格式"""
        results = []
        for item in items:
            if self._is_invalid_item(item.name):
                continue
            value_numeric = None
            try:
                value_numeric = float(item.result.replace(" ", ""))
            except ValueError:
                pass

            ref_low = None
            ref_high = None
            ref_text = None

            ref_match = re.search(r"([\d.]+)\s*[-~—–]+\s*([\d.]+)", item.ref_range)
            if ref_match:
                ref_low_str = ref_match.group(1).replace(" ", "")
                ref_high_str = ref_match.group(2).replace(" ", "")
                ref_text = f"{ref_low_str}-{ref_high_str}"
                try:
                    ref_low = float(ref_low_str)
                    ref_high = float(ref_high_str)
                except ValueError:
                    pass

            if not ref_low and ("<" in item.ref_range or "≤" in item.ref_range):
                match = re.search(r"[<≤]\s*([\d.]+)", item.ref_range)
                if match:
                    try:
                        ref_high = float(match.group(1))
                    except ValueError:
                        pass
                    ref_text = item.ref_range

            flag = None
            if value_numeric is not None:
                if ref_high is not None and value_numeric > ref_high:
                    flag = "↑"
                if ref_low is not None and value_numeric < ref_low:
                    flag = "↓"

            results.append(ParsedResult(
                raw_item_name=item.name,
                raw_value=item.result,
                value_numeric=value_numeric,
                unit=item.unit,
                reference_low=ref_low,
                reference_high=ref_high,
                reference_text=ref_text or (item.ref_range if not ref_low else None),
                flag=flag,
                page_no=page_no,
                ocr_confidence=95.0,
            ))

        return results

    def _calculate_quality_score(self, report: ParsedReport) -> float:
        """计算报告质量分"""
        score = 60.0

        if report.patient_name:
            score += 5
        if report.gender:
            score += 3
        if report.age:
            score += 2
        if report.sample_time:
            score += 5
        if report.report_time:
            score += 5

        if report.results:
            score += 10
            has_ref = sum(1 for r in report.results if r.reference_low is not None)
            if report.results:
                ref_ratio = has_ref / len(report.results)
                score += ref_ratio * 10
        else:
            score = 0.0

        return min(score, 100.0)
