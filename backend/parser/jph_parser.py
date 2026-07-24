"""江苏省人民医院专用解析器

基于OCR坐标数据进行精准解析，支持单栏和双栏布局。

报告特征（横向分辨率约1600）：
1. 医院标识：江苏省人民医院
2. 双栏布局（血常规等）：左栏和右栏各有一套表头
3. 单栏布局（生化全套、乙肝5项等）：单列数据
4. 表头字段：简称、项目名称、结果、单位、参考范围
5. 代号和项目名称分开显示：ALT | *△丙氨酸氨基转移酶
"""
import re
from typing import List, Optional

from .lab_result_parser import ParsedResult, ParsedReport

UNIT_PATTERN = r"(IU/mL|U/mL|ng/mL|ng/L|pg/mL|[μu]mol/L|mmo[Ll]/L|g/L|mg/L|U/L|%)"
UNIT_PATTERN_EXTENDED = r"(IU/mL|U/mL|ng/mL|ng/L|pg/mL|[μu]mol/L|mmo[Ll]/L|g/L|mg/L|U/L|%|10°/L|1012/L|fL|pg|1/n)"


class JPHParser:
    """江苏省人民医院专用解析器"""

    HOSPITAL_NAMES = ["江苏省人民医院"]

    PATIENT_PATTERNS = {
        "name": [
            r"姓名[：:]\s*([\u4e00-\u9fa5]{2,4})",
            r"姓\s*名\s*([\u4e00-\u9fa5]{2,4})",
        ],
        "gender": [
            r"性别[：:]\s*([男女])",
            r"性\s*别\s*([男女])",
        ],
        "age": [
            r"年龄[：:]\s*(\d{1,3})\s*岁?",
            r"年\s*龄\s*(\d{1,3})\s*岁?",
        ],
        "sample_time": [
            r"采样时间[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
            r"采集时间[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
        ],
        "report_time": [
            r"报告时间[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
        ],
    }

    def parse(self, text: str, page_no: int = 1) -> ParsedReport:
        """解析江苏省人民医院报告"""
        report = ParsedReport()

        if not text:
            return report

        report.hospital_name = "江苏省人民医院"

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

    def _parse_ocr_text(self, text: str) -> List:
        """解析OCR坐标文本"""
        items = []
        lines = text.split("\n")
        for line in lines:
            match = re.match(
                r"\(([\d.]+),([\d.]+),([\d.]+)x([\d.]+)\)\s+conf=([\d.]+)\s+text=(.+)",
                line,
            )
            if match:
                items.append(
                    {
                        "x": float(match.group(1)),
                        "y": float(match.group(2)),
                        "width": float(match.group(3)),
                        "height": float(match.group(4)),
                        "conf": float(match.group(5)),
                        "text": match.group(6),
                    }
                )
        return items

    def _is_header_text(self, text: str) -> bool:
        """判断是否为表头文本"""
        headers = ["简称", "项目名称", "结果", "单位", "参考范围"]
        if len(text) > 15:
            return False
        return any(h in text for h in headers)

    def _detect_layout(self, header_items: List) -> str:
        """检测布局类型"""
        header_counts = {}
        for item in header_items:
            for h in ["简称", "项目名称", "结果", "单位", "参考范围"]:
                if h in item["text"]:
                    header_counts[h] = header_counts.get(h, 0) + 1

        if any(count >= 2 for count in header_counts.values()):
            return "double"

        return "single"

    def _detect_column_boundaries(self, header_items: List) -> dict:
        """动态检测各列的边界位置"""
        boundaries = {
            "code": 0,
            "name": 0,
            "result": 0,
            "unit": 0,
            "ref_range": 0,
            "is_double": False,
            "split_x": 800,
            "right_code": 0,
            "right_name": 0,
            "right_result": 0,
            "right_unit": 0,
            "right_ref_range": 0,
        }

        code_positions = []
        name_positions = []
        result_positions = []
        unit_positions = []
        ref_positions = []
        unit_end_positions = []

        for item in header_items:
            text = item["text"]
            x = item["x"]
            w = item.get("w", 0)
            if "简称" in text or "代号" in text:
                code_positions.append(x)
            if "项目名称" in text:
                name_positions.append(x)
            if "结果" in text:
                result_positions.append(x)
            if "单位" in text:
                unit_positions.append(x)
                unit_end_positions.append(x + w)
            if "参考" in text or "参考范围" in text:
                ref_positions.append(x)

        code_positions.sort()
        name_positions.sort()
        result_positions.sort()
        unit_positions.sort()
        ref_positions.sort()

        if len(result_positions) >= 2 and result_positions[1] - result_positions[0] > 300:
            boundaries["is_double"] = True
            boundaries["split_x"] = (result_positions[0] + result_positions[1]) / 2

            boundaries["result"] = result_positions[0]
            boundaries["right_result"] = result_positions[1]

            boundaries["code"] = code_positions[0] + 80 if code_positions else 180
            boundaries["right_code"] = code_positions[1] + 80 if len(code_positions) > 1 else boundaries["split_x"] + 80

            boundaries["name"] = name_positions[0] + 250 if name_positions else boundaries["code"] + 250
            boundaries["right_name"] = name_positions[1] + 250 if len(name_positions) > 1 else boundaries["right_result"] - 100

            boundaries["unit"] = unit_positions[0] if unit_positions else boundaries["result"] + 100
            boundaries["right_unit"] = unit_positions[1] if len(unit_positions) > 1 else boundaries["right_result"] + 100

            boundaries["ref_range"] = ref_positions[0] if ref_positions else boundaries["unit"] + 80
            boundaries["right_ref_range"] = ref_positions[1] if len(ref_positions) > 1 else boundaries["right_unit"] + 80

            if boundaries["is_double"]:
                boundaries["left_ref_end"] = name_positions[1] if len(name_positions) > 1 else boundaries["split_x"]
            else:
                boundaries["left_ref_end"] = boundaries["ref_range"] + 150
        else:
            boundaries["result"] = result_positions[0] if result_positions else 600

            boundaries["code"] = code_positions[0] + 80 if code_positions else 180

            boundaries["name"] = name_positions[0] + 300 if name_positions else boundaries["code"] + 300

            boundaries["unit"] = (unit_positions[0] - 15) if unit_positions else boundaries["result"] + 150

            if unit_end_positions:
                boundaries["ref_range"] = unit_end_positions[0]
            elif ref_positions:
                boundaries["ref_range"] = ref_positions[0]
            else:
                boundaries["ref_range"] = (unit_positions[0] + 120) if unit_positions else boundaries["unit"] + 120

        return boundaries

    def _parse_table_from_coords(self, ocr_items: List) -> List:
        """从OCR坐标解析表格数据"""
        header_items = [i for i in ocr_items if self._is_header_text(i["text"])]
        if not header_items:
            return []

        boundaries = self._detect_column_boundaries(header_items)

        if boundaries["is_double"]:
            return self._parse_double_column_coords(ocr_items)
        else:
            return self._parse_single_column_coords_dynamic(ocr_items, boundaries)

    def _parse_double_column_coords(self, ocr_items: List) -> List:
        """解析双栏布局（生化全套、血常规等，分辨率约1600）"""
        items = []

        header_items = [i for i in ocr_items if self._is_header_text(i["text"])]
        if not header_items:
            return items

        min_y = max(i["y"] for i in header_items) + 10
        max_y = min(i["y"] for i in header_items) + 1200

        data_items = [i for i in ocr_items if min_y < i["y"] < max_y and not self._is_header_text(i["text"])]

        rows = self._group_by_row(data_items)

        for row in rows:
            left_item = {"code": "", "name": "", "result": "", "unit": "", "ref_range": ""}
            right_item = {"code": "", "name": "", "result": "", "unit": "", "ref_range": ""}

            for i in row:
                if i["x"] < 800:
                    if i["x"] < 170:
                        if re.match(r"^[A-Z0-9/\-._]+$", i["text"]) and len(i["text"]) <= 15:
                            left_item["code"] = i["text"]
                        else:
                            left_item["name"] += i["text"]
                    elif i["x"] < 465:
                        left_item["name"] += i["text"]
                    elif i["x"] < 560:
                        if re.search(UNIT_PATTERN_EXTENDED, i["text"]):
                            self._parse_merged_cell(i["text"], left_item)
                        elif re.search(r"[-~—–≤≥]", i["text"]):
                            left_item["ref_range"] += i["text"]
                        else:
                            left_item["result"] += i["text"]
                    elif i["x"] < 640:
                        text = i["text"]
                        arrow_match = re.match(r"^([↑↓])(.*)", text)
                        if arrow_match:
                            left_item["result"] += arrow_match.group(1)
                            text = arrow_match.group(2)
                        
                        if re.search(r"--|[-~—–≤≥]", text):
                            ref_patterns = [
                                r"(\d+[\d.\s]*--[\d.\s]+\d)",
                                r"(\d+\.?\d*\s*[-~—–]\s*\d+\.?\d*)",
                                r"([≤≥<>]\s*\d+\.?\d*)",
                            ]
                            ref_match = None
                            for pattern in ref_patterns:
                                ref_match = re.search(pattern, text)
                                if ref_match:
                                    break
                            if ref_match:
                                ref_part = ref_match.group(1).replace(" ", "")
                                text = text[:ref_match.start()]
                                if not left_item["ref_range"]:
                                    left_item["ref_range"] = ref_part
                        
                        left_item["unit"] += text
                    else:
                        left_item["ref_range"] += i["text"]
                else:
                    if i["x"] < 930:
                        text = i["text"]
                        code_match = re.match(r"^(\d+)\s*([A-Z0-9/\-._]+)\s*", text)
                        if code_match:
                            right_item["code"] = code_match.group(2)
                            text = text[code_match.end():]
                        num_match = re.search(r"\s+(\d+\.?\d*)\s*([↑↓])?$", text)
                        if num_match and len(text) > 15:
                            right_item["name"] += text[:num_match.start()].strip()
                            right_item["result"] += num_match.group(1)
                            if num_match.group(2):
                                right_item["result"] += num_match.group(2)
                        else:
                            right_item["name"] += text
                    elif i["x"] < 1195:
                        right_item["name"] += i["text"]
                    elif i["x"] < 1260:
                        text = i["text"]
                        if re.search(UNIT_PATTERN_EXTENDED, text):
                            if re.search(r"--|[-~—–≤≥]", text):
                                ref_patterns = [
                                    r"(\d+[\d.\s]*--[\d.\s]+\d)",
                                    r"(\d+\.?\d*\s*[-~—–]\s*\d+\.?\d*)",
                                    r"([≤≥<>]\s*\d+\.?\d*)",
                                ]
                                ref_match = None
                                for pattern in ref_patterns:
                                    ref_match = re.search(pattern, text)
                                    if ref_match:
                                        break
                                if ref_match:
                                    ref_part = ref_match.group(1).replace(" ", "")
                                    text = text[:ref_match.start()]
                                    if not right_item["ref_range"]:
                                        right_item["ref_range"] = ref_part
                            unit_patterns = [
                                UNIT_PATTERN,
                                r"(COI|NT-proBNP|fL|pg|10°/L|1012/L|1/n)",
                            ]
                            unit_match = None
                            for pattern in unit_patterns:
                                unit_match = re.search(pattern, text)
                                if unit_match:
                                    break
                            if unit_match:
                                unit_part = unit_match.group(1)
                                text = text[:unit_match.start()] + text[unit_match.end():]
                                if not right_item["unit"]:
                                    right_item["unit"] = unit_part
                            arrow_match = re.search(r"([↑↓])", text)
                            arrow_part = arrow_match.group(1) if arrow_match else ""
                            numeric_match = re.search(r"([\d.]+)", text)
                            if numeric_match:
                                right_item["result"] += numeric_match.group(1) + arrow_part
                            else:
                                right_item["result"] += text + arrow_part
                        elif re.search(r"[-~—–≤≥]", text):
                            right_item["ref_range"] += text
                        else:
                            right_item["result"] += text
                    elif i["x"] < 1380:
                        text = i["text"]
                        arrow_match = re.match(r"^([↑↓])(.*)", text)
                        if arrow_match:
                            right_item["result"] += arrow_match.group(1)
                            text = arrow_match.group(2)
                        
                        if re.search(r"--|[-~—–≤≥]", text):
                            ref_patterns = [
                                r"(\d+[\d.\s]*--[\d.\s]+\d)",
                                r"(\d+\.?\d*\s*[-~—–]\s*\d+\.?\d*)",
                                r"([≤≥<>]\s*\d+\.?\d*)",
                            ]
                            ref_match = None
                            for pattern in ref_patterns:
                                ref_match = re.search(pattern, text)
                                if ref_match:
                                    break
                            if ref_match:
                                ref_part = ref_match.group(1).replace(" ", "")
                                text = text[:ref_match.start()]
                                if not right_item["ref_range"]:
                                    right_item["ref_range"] = ref_part
                        
                        right_item["unit"] += text
                    else:
                        right_item["ref_range"] += i["text"]

            self._clean_item(left_item)
            self._clean_item(right_item)

            if left_item["name"] and left_item["result"]:
                items.append(left_item)

            if right_item["name"] and right_item["result"]:
                items.append(right_item)

        return items

    def _parse_single_column_coords(self, ocr_items: List) -> List:
        """解析单栏布局（旧版，保留兼容性）"""
        items = []

        header_items = [i for i in ocr_items if self._is_header_text(i["text"])]
        if not header_items:
            return items

        min_y = max(i["y"] for i in header_items) + 10
        max_y = min(i["y"] for i in header_items) + 800

        data_items = [i for i in ocr_items if min_y < i["y"] < max_y and not self._is_header_text(i["text"])]

        rows = self._group_by_row(data_items)

        for row in rows:
            item = {"code": "", "name": "", "result": "", "unit": "", "ref_range": ""}

            for i in row:
                if i["x"] < 170:
                    if re.match(r"^[A-Z0-9/\-._]+$", i["text"]) and len(i["text"]) <= 15:
                        item["code"] = i["text"]
                    else:
                        item["name"] += i["text"]
                elif i["x"] < 465:
                    item["name"] += i["text"]
                elif i["x"] < 560:
                    if re.search(UNIT_PATTERN, i["text"]):
                        if re.match(r"^[↑↓].*" + UNIT_PATTERN, i["text"]):
                            arrow_match = re.match(r"^([↑↓])(.*)", i["text"])
                            if arrow_match:
                                item["result"] += arrow_match.group(1)
                                item["unit"] += arrow_match.group(2)
                        else:
                            self._parse_merged_cell(i["text"], item)
                    elif re.search(r"[-~—–≤≥]", i["text"]):
                        item["ref_range"] += i["text"]
                    else:
                        item["result"] += i["text"]
                elif i["x"] < 650:
                    text = i["text"]
                    if re.match(r"^[↑↓].*" + UNIT_PATTERN, text):
                        arrow_match = re.match(r"^([↑↓])(.*)", text)
                        if arrow_match:
                            item["result"] += arrow_match.group(1)
                            text = arrow_match.group(2)
                    
                    if re.search(r"--|[-~—–≤≥]", text):
                        ref_patterns = [
                            r"(\d+[\d.\s]*--[\d.\s]+\d)",
                            r"(\d+\.?\d*\s*[-~—–]\s*\d+\.?\d*)",
                            r"([≤≥<>]\s*\d+\.?\d*)",
                        ]
                        ref_match = None
                        for pattern in ref_patterns:
                            ref_match = re.search(pattern, text)
                            if ref_match:
                                break
                        if ref_match:
                            ref_part = ref_match.group(1).replace(" ", "")
                            text = text[:ref_match.start()]
                            if not item["ref_range"]:
                                item["ref_range"] = ref_part
                    
                    item["unit"] += text
                else:
                    item["ref_range"] += i["text"]

            self._clean_item(item)

            if item["name"] and item["result"]:
                items.append(item)

        return items

    def _parse_single_column_coords_dynamic(self, ocr_items: List, boundaries: dict) -> List:
        """动态解析单栏布局"""
        items = []

        header_items = [i for i in ocr_items if self._is_header_text(i["text"])]
        if not header_items:
            return items

        min_y = max(i["y"] for i in header_items) + 10
        max_y = min(i["y"] for i in header_items) + 800

        data_items = [i for i in ocr_items if min_y < i["y"] < max_y and not self._is_header_text(i["text"])]

        rows = self._group_by_row(data_items)

        code_end = boundaries["code"]
        name_end = boundaries["name"]
        result_start = boundaries["result"]
        unit_start = boundaries["unit"]
        ref_start = boundaries["ref_range"]

        for row in rows:
            item = {"code": "", "name": "", "result": "", "unit": "", "ref_range": ""}

            for i in row:
                if i["x"] < code_end:
                    if re.match(r"^[A-Z0-9/\-._]+$", i["text"]) and len(i["text"]) <= 15:
                        item["code"] = i["text"]
                    else:
                        item["name"] += i["text"]
                elif i["x"] < name_end:
                    item["name"] += i["text"]
                elif i["x"] < unit_start:
                    if re.search(UNIT_PATTERN, i["text"]):
                        self._parse_merged_cell(i["text"], item)
                    elif re.search(r"[-~—–≤≥]", i["text"]):
                        item["ref_range"] += i["text"]
                    else:
                        if len(i["text"]) == 1 and re.match(r"^\d$", i["text"]) and item["result"]:
                            pass
                        else:
                            item["result"] += i["text"]
                elif i["x"] < ref_start:
                    if re.search(UNIT_PATTERN, i["text"]):
                        self._parse_merged_cell(i["text"], item)
                    elif re.match(r"^[↑↓].*(IU/mL|U/mL|ng/mL|ng/L|pg/mL|μmol/L|mmol/L|g/L|mg/L|U/L|%)", i["text"]):
                        arrow_match = re.match(r"^([↑↓])(.*)", i["text"])
                        if arrow_match:
                            item["result"] += arrow_match.group(1)
                            item["unit"] += arrow_match.group(2)
                    else:
                        if len(i["text"]) == 1 and re.match(r"^\d$", i["text"]) and item["unit"]:
                            pass
                        else:
                            item["unit"] += i["text"]
                else:
                    item["ref_range"] += i["text"]

            self._clean_item(item)

            if item["name"] and item["result"]:
                items.append(item)

        return items

    def _parse_double_column_coords_dynamic(self, ocr_items: List, boundaries: dict) -> List:
        """动态解析双栏布局"""
        items = []

        header_items = [i for i in ocr_items if self._is_header_text(i["text"])]
        if not header_items:
            return items

        min_y = max(i["y"] for i in header_items) + 10
        max_y = min(i["y"] for i in header_items) + 1000

        data_items = [i for i in ocr_items if min_y < i["y"] < max_y and not self._is_header_text(i["text"])]

        rows = self._group_by_row(data_items)

        split_x = boundaries["split_x"]
        left_ref_end = boundaries.get("left_ref_end", split_x)

        left_code_end = boundaries["code"]
        left_name_end = boundaries["name"]
        left_result_start = boundaries["result"]
        left_unit_start = boundaries["unit"]
        left_ref_start = boundaries["ref_range"]

        right_code_end = boundaries["right_code"]
        right_name_end = boundaries["right_name"]
        right_result_start = boundaries["right_result"]
        right_unit_start = boundaries["right_unit"]
        right_ref_start = boundaries["right_ref_range"]

        for row in rows:
            left_item = {"code": "", "name": "", "result": "", "unit": "", "ref_range": ""}
            right_item = {"code": "", "name": "", "result": "", "unit": "", "ref_range": ""}

            for i in row:
                if i["x"] < left_ref_end:
                    if i["x"] < left_code_end:
                        if re.match(r"^[A-Z0-9/\-._]+$", i["text"]) and len(i["text"]) <= 15:
                            left_item["code"] = i["text"]
                        else:
                            left_item["name"] += i["text"]
                    elif i["x"] < left_name_end:
                        left_item["name"] += i["text"]
                    elif i["x"] < left_unit_start:
                        if re.search(UNIT_PATTERN, i["text"]):
                            self._parse_merged_cell(i["text"], left_item)
                        elif re.search(r"[-~—–≤≥]", i["text"]):
                            left_item["ref_range"] += i["text"]
                        else:
                            left_item["result"] += i["text"]
                    elif i["x"] < left_ref_start:
                        left_item["unit"] += i["text"]
                    else:
                        left_item["ref_range"] += i["text"]
                elif i["x"] >= split_x:
                    if i["x"] < right_code_end:
                        if re.match(r"^[A-Z0-9/\-._]+$", i["text"]) and len(i["text"]) <= 15:
                            right_item["code"] = i["text"]
                        else:
                            right_item["name"] += i["text"]
                    elif i["x"] < right_name_end:
                        right_item["name"] += i["text"]
                    elif i["x"] < right_unit_start:
                        if re.search(UNIT_PATTERN, i["text"]):
                            self._parse_merged_cell(i["text"], right_item)
                        elif re.search(r"[-~—–≤≥]", i["text"]):
                            right_item["ref_range"] += i["text"]
                        else:
                            right_item["result"] += i["text"]
                    elif i["x"] < right_ref_start:
                        if re.match(r"^[↑↓].*(IU/mL|U/mL|ng/mL|pg/mL|μmol/L|mmol/L|g/L|mg/L|U/L|%)", i["text"]):
                            arrow_match = re.match(r"^([↑↓])(.*)", i["text"])
                            if arrow_match:
                                right_item["result"] += arrow_match.group(1)
                                right_item["unit"] += arrow_match.group(2)
                        else:
                            right_item["unit"] += i["text"]
                    else:
                        right_item["ref_range"] += i["text"]

            self._clean_item(left_item)
            self._clean_item(right_item)

            if left_item["name"] and left_item["result"]:
                items.append(left_item)

            if right_item["name"] and right_item["result"]:
                items.append(right_item)

        return items

    def _clean_item(self, item: dict):
        """清理项目数据"""
        item["name"] = item["name"].strip()
        item["result"] = item["result"].strip().replace(" ", "")
        item["unit"] = item["unit"].strip()
        item["ref_range"] = item["ref_range"].strip()

        item["name"] = item["name"].replace("*", "")
        item["name"] = item["name"].replace("△", "")
        item["name"] = item["name"].replace("＊", "")
        
        item["name"] = re.sub(r"[（\(]干化学法[）\)]", "", item["name"])
        item["name"] = re.sub(r"[（\(][^）\)]+[）\)]", "", item["name"])
        
        item["name"] = re.sub(r"^\d+\s*", "", item["name"])
        item["name"] = re.sub(r"^\[\d+", "", item["name"])
        
        item["name"] = re.sub(r"^[A-Z][A-Za-z0-9/\-._]*\s*[%#]?\s*", "", item["name"])
        item["name"] = re.sub(r"^[A-Za-z0-9/\-._]+\s+[*△＊]?\s*", "", item["name"])
        item["name"] = re.sub(r"^[A-Za-z0-9/\-._]+[\s]*[*△＊]+\s*", "", item["name"])
        
        item["name"] = re.sub(r"^-\s*", "", item["name"])
        item["name"] = re.sub(r"^eGFR\s*", "", item["name"])
        item["name"] = re.sub(r"^CMV-DNA\s*", "", item["name"])
        item["name"] = re.sub(r"^EB-?DNA\s*", "", item["name"])
        item["name"] = re.sub(r"^EB病毒\s*", "", item["name"])
        item["name"] = re.sub(r"^COBAS\s*", "", item["name"])
        item["name"] = re.sub(r"^D-Dime\s*", "", item["name"])
        item["name"] = re.sub(r"^PCR\s*", "", item["name"])
        item["name"] = re.sub(r"^typing\s+[a-zA-Z]+\s*", "", item["name"])
        item["name"] = re.sub(r"^Phagocyte-ST\s*", "", item["name"])
        item["name"] = re.sub(r"^PIVKA-\s*", "", item["name"])
        item["name"] = re.sub(r"^MALB(?:/[a-zA-Z]+)?\s*", "", item["name"])
        item["name"] = re.sub(r"^u-TP(?:/[a-zA-Z]+)?\s*", "", item["name"])
        item["name"] = re.sub(r"^hs-[a-zA-Z]+\s*", "", item["name"])
        item["name"] = re.sub(r"^hs[CR]+\s*", "", item["name"])
        item["name"] = re.sub(r"^TPOAB\s*", "", item["name"])
        item["name"] = re.sub(r"^TNF-\s*", "", item["name"])
        item["name"] = re.sub(r"^TSH\s*\*\s*", "", item["name"])
        item["name"] = re.sub(r"^UCREA\s*", "", item["name"])
        item["name"] = re.sub(r"^UCB\s*", "", item["name"])
        item["name"] = re.sub(r"^NEUT%\s*", "", item["name"])
        item["name"] = re.sub(r"^LYMPH%\s*", "", item["name"])
        item["name"] = re.sub(r"^EO#\s*", "", item["name"])
        item["name"] = re.sub(r"^N端-前脑钠肽\s*", "", item["name"])
        item["name"] = re.sub(r"^C-Ca\s*", "", item["name"])
        item["name"] = re.sub(r"^-3-β-D-\s*", "", item["name"])
        item["name"] = re.sub(r"^Y-\s*", "", item["name"])
        item["name"] = re.sub(r"^Ca\s*", "", item["name"])
        
        item["name"] = re.sub(r"^>\s*[\d.]+\s*", "", item["name"])
        item["name"] = re.sub(r"^<\s*[\d.]+\s*", "", item["name"])
        
        if re.match(r"^α-羟丁酸脱氢酶\s+[\d]", item["name"]):
            item["name"] = "α-羟丁酸脱氢酶"
        elif re.match(r"^β2微球蛋白\s+[\d]", item["name"]):
            item["name"] = "β2微球蛋白"
        
        item["name"] = re.sub(r"\s+", " ", item["name"]).strip()

        self._split_name_with_result(item)
        self._split_unit_ref(item)
        self._split_result_unit(item)

    def _split_name_with_result(self, item: dict):
        """处理名称中包含数值的情况（如AST*△天门冬氨酸氨基转移酶(干化学法)62.8）"""
        if item["name"]:
            name = item["name"]
            
            patterns = [
                r"(.+[（\(]干化学法[）\)])([↑↓]?)([\d.]+)",
                r"(.+[（\(][^）\)]+[）\)])([↑↓]?)([\d.]+)",
                r"(.+?)([↑↓]?)([\d.]+)$",
            ]
            
            for pattern in patterns:
                match = re.match(pattern, name)
                if match:
                    item["name"] = match.group(1).strip()
                    arrow = match.group(2) or ""
                    num = match.group(3) or ""
                    if num:
                        existing_result = item["result"] or ""
                        if arrow and not existing_result:
                            item["result"] = num + arrow
                        elif existing_result and not arrow:
                            item["result"] = num + existing_result
                        else:
                            item["result"] = num + existing_result + arrow
                    break

    def _group_by_row(self, items: List, y_threshold: float = 20.0) -> List[List]:
        """按Y坐标分组为行"""
        if not items:
            return []

        items.sort(key=lambda i: i["y"])
        rows = []
        current_row = [items[0]]

        for item in items[1:]:
            if item["y"] - current_row[0]["y"] <= y_threshold:
                current_row.append(item)
            else:
                rows.append(current_row)
                current_row = [item]

        if current_row:
            rows.append(current_row)

        return rows

    def _split_unit_ref(self, item: dict):
        """拆分单位和参考范围合并的情况"""
        if item["unit"] and not item["ref_range"]:
            unit_text = item["unit"]
            ref_patterns = [
                r"(\d+\.?\d*(?:\s+\d+)?)\s*[-~—–]\s*(\d+\.?\d*(?:\s+\d+)?)",
                r"([≤≥<>]\s*\d+\.?\d*)",
                r"(\d+\.?\d*\s*[≤≥<>])",
            ]
            ref_match = None
            for pattern in ref_patterns:
                ref_match = re.search(pattern, unit_text)
                if ref_match:
                    break
            
            if ref_match:
                ref_part = ref_match.group(1).replace(" ", "")
                item["ref_range"] = ref_part
                item["unit"] = unit_text[:ref_match.start()].strip()

        if item["ref_range"] and re.search(r"[\u4e00-\u9fa5]{2,}", item["ref_range"]):
            ref_text = item["ref_range"]
            method_match = re.search(r"[\u4e00-\u9fa5]{2,}$", ref_text)
            if method_match:
                item["ref_range"] = ref_text[:method_match.start()].strip()

        if item["result"] and not item["ref_range"]:
            result_text = item["result"]
            ref_match = re.search(r"(\d+\.?\d*(?:\s+\d+)?)\s*[-~—–≤≥]\s*(\d+\.?\d*(?:\s+\d+)?)", result_text)
            if ref_match:
                start = ref_match.group(1).replace(" ", "")
                end = ref_match.group(2).replace(" ", "") if ref_match.group(2) else ""
                if end:
                    item["ref_range"] = f"{start}-{end}"
                else:
                    item["ref_range"] = ref_match.group(0).replace(" ", "")
                item["result"] = result_text[:ref_match.start()].strip()

    def _parse_merged_cell(self, text: str, item: dict):
        """解析OCR合并的单元格（结果/单位/参考范围合并在一起）"""
        ref_patterns = [
            r"(\d+[\d.\s]*--[\d.\s]+\d)",
            r"(\d+\.?\d*\s*[-~—–]\s*\d+\.?\d*)",
            r"([≤≥<>]\s*\d+\.?\d*)",
            r"(\d+\.?\d*\s*[≤≥<>])",
        ]
        ref_match = None
        for pattern in ref_patterns:
            ref_match = re.search(pattern, text)
            if ref_match:
                break
        
        if ref_match:
            ref_part = ref_match.group(1).replace(" ", "")
            text = text[:ref_match.start()] + text[ref_match.end():]
            if not item["ref_range"]:
                item["ref_range"] = ref_part
        
        unit_patterns = [
            UNIT_PATTERN,
            r"(COI|NT-proBNP|fL|pg|10°/L|1012/L)",
            r"(1/n)",
        ]
        unit_match = None
        for pattern in unit_patterns:
            unit_match = re.search(pattern, text)
            if unit_match:
                break
        
        if unit_match:
            unit_part = unit_match.group(1)
            text = text[:unit_match.start()] + text[unit_match.end():]
            if not item["unit"]:
                item["unit"] = unit_part
        
        full_match = re.match(r"([↑↓]?)\s*([\d.]+)\s*([↑↓]?)", text.strip())
        if full_match:
            arrow1 = full_match.group(1)
            num_part = full_match.group(2)
            arrow2 = full_match.group(3)
            item["result"] += num_part + arrow1 + arrow2
        else:
            numeric_match = re.search(r"([\d.]+)", text)
            if numeric_match:
                num_part = numeric_match.group(1)
                arrow_match = re.search(r"([↑↓])", text)
                arrow_part = arrow_match.group(1) if arrow_match else ""
                item["result"] += num_part + arrow_part
            else:
                item["result"] += text

    def _split_result_unit(self, item: dict):
        """拆分结果和单位合并的情况"""
        result_text = item["result"]
        if result_text and not item["unit"]:
            full_patterns = [
                r"([\d.]+)\s*([↑↓]?)\s*(IU/mL|U/mL|ng/mL|pg/mL|μmol/L|mmol/L|g/L|mg/L|U/L|%)\s*(\d+\.?\d*\s*[-~—–≤≥]\s*\d+\.?\d*)?",
                r"([↑↓]?)\s*([\d.]+)\s*(IU/mL|U/mL|ng/mL|pg/mL|μmol/L|mmol/L|g/L|mg/L|U/L|%)\s*(\d+\.?\d*\s*[-~—–≤≥]\s*\d+\.?\d*)?",
                r"([\d.]+)\s*(IU/mL|U/mL|ng/mL|pg/mL|μmol/L|mmol/L|g/L|mg/L|U/L|%)\s*([↑↓]?)\s*(\d+\.?\d*\s*[-~—–≤≥]\s*\d+\.?\d*)?",
            ]
            for pattern in full_patterns:
                full_match = re.match(pattern, result_text)
                if full_match:
                    num_part = full_match.group(1) if re.match(r"[\d.]", full_match.group(1)) else full_match.group(2)
                    arrow_part = full_match.group(2) if re.match(r"[↑↓]", full_match.group(2)) else (full_match.group(3) if re.match(r"[↑↓]", full_match.group(3)) else "")
                    unit_part = full_match.group(3) if re.match(r"[A-Za-z/μ]", full_match.group(3)) else (full_match.group(2) if re.match(r"[A-Za-z/μ]", full_match.group(2)) else full_match.group(4))
                    ref_part = None
                    for g in [4, 3, 2]:
                        if g <= len(full_match.groups()) and full_match.group(g) and re.search(r"[-~—–≤≥]", full_match.group(g)):
                            ref_part = full_match.group(g)
                            break
                    
                    item["result"] = num_part + arrow_part
                    item["unit"] = unit_part
                    if ref_part:
                        item["ref_range"] = ref_part.replace(" ", "")
                    return

            unit_at_start = re.match(r"(IU/mL|U/mL|ng/mL|pg/mL|μmol/L|mmol/L|g/L|mg/L|U/L|%)\s*([↑↓]?)\s*([\d.]+)", result_text)
            if unit_at_start:
                item["unit"] = unit_at_start.group(1)
                item["result"] = unit_at_start.group(3) + (unit_at_start.group(2) or "")
                return

            numeric_with_unit = re.search(r"([\d.]+)\s*([↑↓])?\s*(IU/mL|U/mL|ng/mL|pg/mL|μmol/L|mmol/L|g/L|mg/L|U/L|%)", result_text)
            if numeric_with_unit:
                item["result"] = numeric_with_unit.group(1) + (numeric_with_unit.group(2) or "")
                item["unit"] = numeric_with_unit.group(3)
                remaining_text = result_text[numeric_with_unit.end():]
                ref_patterns = [
                    r"(\d+\.?\d*\s*[-~—–]\s*\d+\.?\d*)",
                    r"([≤≥<>]\s*\d+\.?\d*)",
                ]
                for pattern in ref_patterns:
                    ref_match = re.search(pattern, remaining_text)
                    if ref_match:
                        item["ref_range"] = ref_match.group(1).replace(" ", "")
                        break
                if not item["ref_range"]:
                    for pattern in ref_patterns:
                        ref_match = re.search(pattern, result_text)
                        if ref_match:
                            item["ref_range"] = ref_match.group(1).replace(" ", "")
                            break
                return

            arrow_with_unit = re.match(r"([↑↓]?)\s*(IU/mL|U/mL|ng/mL|pg/mL|μmol/L|mmol/L|g/L|mg/L|U/L|%)\s*([\d.]+)", result_text)
            if arrow_with_unit:
                item["result"] = arrow_with_unit.group(3) + (arrow_with_unit.group(1) or "")
                item["unit"] = arrow_with_unit.group(2)
                return

            unit_patterns = [
                r"([\d.]+)\s*(IU/mL|U/mL|ng/mL|pg/mL|μmol/L|mmol/L|g/L|mg/L|U/L|%|10°/L)",
                r"([\d.]+)\s*(COI|NT-proBNP)",
            ]
            for pattern in unit_patterns:
                match = re.search(pattern, result_text)
                if match:
                    item["result"] = match.group(1)
                    item["unit"] = match.group(2)
                    break

            if not item["unit"]:
                chinese_with_number = re.search(r"([\u4e00-\u9fa5]+[\d.]+)", result_text)
                if chinese_with_number:
                    item["result"] = chinese_with_number.group(1)

        if item["result"] and not item["unit"]:
            numeric_match = re.search(r"([\d.]+)\s*([A-Za-z/μ]+)$", item["result"])
            if numeric_match:
                item["result"] = numeric_match.group(1)
                item["unit"] = numeric_match.group(2)

    def _is_invalid_item(self, name: str, result: str) -> bool:
        """判断是否为无效条目（如申请医师、检验者等）"""
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
            if keyword in name or keyword in result:
                return True
        
        if not name or not result:
            return True
        
        if name.startswith("(cid:"):
            return True
        
        if name in ["≤", "≥", "/", "α", "β"]:
            return True
        
        if len(name) > 50 and len(result) < 5:
            return True
        
        if re.match(r"^[<>]?\s*[\d.]+\s*$", name):
            return True
        
        if re.match(r"^[αβγδθλμνπσφψω]$", name):
            return True
        
        return False

    def _convert_to_parsed_results(self, items: List, page_no: int) -> List[ParsedResult]:
        """转换为标准ParsedResult格式"""
        results = []
        for idx, item in enumerate(items):
            raw_name = item.get("name", "")
            raw_result = item.get("result", "")
            raw_unit = item.get("unit", "")
            raw_ref = item.get("ref_range", "")
            code = item.get("code", "")
            
            if self._is_invalid_item(raw_name, raw_result):
                continue

            ref_range = self._clean_ref_range(raw_ref)

            result = ParsedResult(
                raw_item_name=raw_name,
                raw_value=raw_result
            )
            result.value_numeric = self._extract_numeric_value(raw_result)
            result.unit = raw_unit
            result.reference_text = ref_range
            result.page_no = page_no
            result.code = code

            result.flag = self._detect_abnormal(raw_result, ref_range)

            results.append(result)

        return results

    def _clean_ref_range(self, ref: str) -> str:
        """清理参考范围，处理带空格格式如1. 2--2.4"""
        if not ref:
            return ""

        ref = ref.strip()

        symbol_match = re.search(r"([≤≥<>])", ref)
        if symbol_match:
            num_match = re.search(r"(\d+\.?\d*(?:\s+\d+)?)", ref)
            if num_match:
                return f"{symbol_match.group(1)}{num_match.group(1).replace(' ', '')}"

        match = re.search(r"(\d+\.?\d*(?:\s+\d+)?)", ref)
        if match:
            start = match.group(1).replace(" ", "")
            ref = ref[match.end():]

            match2 = re.search(r"[-~—–]\s*(\d+\.?\d*(?:\s+\d+)?)", ref)
            if match2:
                end = match2.group(1).replace(" ", "")
                return f"{start}-{end}"

        return ref

    def _extract_numeric_value(self, result_str: str) -> Optional[float]:
        """从结果字符串中提取数值"""
        match = re.search(r"([\d.]+)", result_str)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None

    def _detect_abnormal(self, result: str, ref_range: str) -> Optional[str]:
        """检测异常标志"""
        if "↑" in result or "↑" in ref_range:
            return "H"
        if "↓" in result or "↓" in ref_range:
            return "L"
        return None

    def _calculate_quality_score(self, report: ParsedReport) -> float:
        """计算质量分数"""
        if not report.results:
            return 0.0

        valid_count = sum(1 for r in report.results if r.value_numeric is not None)
        return min(95.0, valid_count * 3.0)