"""南京市第二医院专用解析器

支持两种解析模式：
1. 纯文本模式：适用于单栏报告
2. 坐标模式：适用于双栏布局报告（如尿液分析）

报告特征：
1. 医院标识：南京市第二医院
2. 单行格式：1 PCT *降钙素原 (发光法) 0.886 ↑ ng/ml 0.000 -0.052 电化学发光法
3. 或：1 *甲型肝炎病毒IgM抗体 HAV-M 5.420 AU/mL 0-20 磁微粒化学发光法
4. 多行参考范围：部分指标的参考范围可能跨多行
5. 结果可能包含标志：↑、↓、阳性、阴性、<、>
6. 双栏布局：尿液分析等报告采用左右双栏布局
"""
import re
from typing import List, Optional, Tuple

from .lab_result_parser import ParsedResult, ParsedReport


class NSHParser:
    """南京市第二医院专用解析器"""

    HOSPITAL_NAMES = ["南京市第二医院"]

    PATIENT_PATTERNS = {
        "name": [
            r"姓\s*名[：:]\s*([\u4e00-\u9fa5]{2,4})",
            r"姓名[：:]\s*([\u4e00-\u9fa5]{2,4})",
        ],
        "gender": [
            r"性\s*别[：:]\s*([男女])",
            r"性别[：:]\s*([男女])",
        ],
        "age": [
            r"年\s*龄[：:]\s*(\d{1,3})\s*岁?",
            r"年龄[：:]\s*(\d{1,3})\s*岁?",
        ],
        "sample_time": [
            r"采集时间[：:]\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
        ],
        "report_time": [
            r"报告时间[：:]\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
        ],
    }

    STOP_PATTERNS = [
        r"解释与建议",
        r"送检医生",
        r"检验者",
        r"审核者",
        r"本结果仅对",
        r"此报告仅对",
        r"采集时间：",
        r"接收时间：",
    ]

    def parse(self, text: str, page_no: int = 1, coords_text: str = "") -> ParsedReport:
        """解析南京市第二医院报告
        
        Args:
            text: 普通文本内容
            page_no: 页码
            coords_text: OCR坐标文本（格式：(x,y,w,h) conf=xx text=xxx）
        """
        report = ParsedReport()

        if not text:
            return report

        report.hospital_name = "南京市第二医院"

        report.patient_name = self._extract(text, "name")
        report.gender = self._extract(text, "gender")
        report.age = self._extract(text, "age")
        report.sample_time = self._extract(text, "sample_time")
        report.report_time = self._extract(text, "report_time")

        if coords_text:
            items = self._parse_table_from_coords(coords_text)
        else:
            items = self._parse_table_from_text(text)

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

    def _parse_table_from_text(self, text: str) -> List[dict]:
        """从文本中解析表格数据（单栏模式）"""
        items = []
        lines = text.split("\n")

        header_line = -1
        for i, line in enumerate(lines):
            if "中文名称" in line and "结果" in line and "单位" in line:
                header_line = i
                break

        if header_line == -1:
            for i, line in enumerate(lines):
                if "项目名称" in line and "结果" in line:
                    header_line = i
                    break

        if header_line == -1:
            for i, line in enumerate(lines):
                if "检验项目" in line and "测定结果" in line:
                    header_line = i
                    break

        if header_line == -1:
            for i, line in enumerate(lines):
                if "检验项目" in line and "结果" in line:
                    header_line = i
                    break

        if header_line == -1:
            for i, line in enumerate(lines):
                if "序号" in line and "项目名称" in line and "结果" in line:
                    header_line = i
                    break

        if header_line == -1:
            for i, line in enumerate(lines):
                if "序号" in line and "缩写" in line and "结果" in line:
                    header_line = i
                    break

        if header_line == -1:
            return items

        data_lines = lines[header_line + 1 :]

        current_item = None
        for line in data_lines:
            line = line.strip()
            if not line:
                continue

            for stop_pattern in self.STOP_PATTERNS:
                if stop_pattern in line:
                    if current_item:
                        items.append(current_item)
                    return items

            is_new_item = False
            item_content = ""
            
            numbered_match = re.match(r"^(\d+)[．.、]\s*(.+)$", line)
            if numbered_match:
                rest = numbered_match.group(2)
                if re.match(r"^[\u4e00-\u9fa5*]", rest) or re.match(r"^[A-Za-z]+", rest):
                    is_new_item = True
                    item_content = rest
            else:
                num_match = re.match(r"^(\d+)\s+(.+)$", line)
                if num_match:
                    rest = num_match.group(2)
                    if re.match(r"^[\u4e00-\u9fa5*]", rest) or re.match(r"^[A-Za-z]+", rest):
                        is_new_item = True
                        item_content = rest
                else:
                    num_match2 = re.match(r"^(\d+)([\u4e00-\u9fa5*].*)$", line)
                    if num_match2:
                        is_new_item = True
                        item_content = num_match2.group(2)

            if is_new_item:
                if current_item:
                    items.append(current_item)

                current_item = {"code": "", "name": "", "result": "", "unit": "", "ref_range": "", "method": ""}
                self._parse_item_content(item_content, current_item)

            elif current_item:
                if re.search(r"[\d.]+[-~—–][\d.]+", line) or "<" in line or ">" in line:
                    current_item["ref_range"] += " " + line.strip()
                elif current_item["ref_range"]:
                    current_item["ref_range"] += " " + line.strip()
                elif current_item["name"] and not current_item["result"]:
                    current_item["name"] += " " + line.strip()

        if current_item:
            items.append(current_item)

        return items

    def _parse_table_from_coords(self, coords_text: str) -> List[dict]:
        """从坐标文本中解析表格数据（支持双栏布局）
        
        改进策略：
        1. 按y坐标分组为行
        2. 检测双栏布局（通过表头位置判断）
        3. 对每行的文本块按x坐标排序后拼接
        4. 分别解析左右两栏
        """
        items = []
        
        blocks = []
        for line in coords_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            match = re.match(r"\((\d+),(\d+),(\d+)x(\d+)\)\s+conf=([\d.]+)\s+text=(.+)", line)
            if match:
                x = int(match.group(1))
                y = int(match.group(2))
                w = int(match.group(3))
                h = int(match.group(4))
                conf = float(match.group(5))
                text = match.group(6)
                
                blocks.append({
                    'x': x,
                    'y': y,
                    'w': w,
                    'h': h,
                    'conf': conf,
                    'text': text
                })
        
        if not blocks:
            return items
        
        header_keys = ["检验项目", "结果", "单位", "参考范围", "参考区间", "测定结果", "项目名称"]
        
        header_blocks = [b for b in blocks if any(k in b['text'] for k in header_keys)]
        if not header_blocks:
            return self._parse_table_from_text(coords_text)
        
        header_y_values = sorted(set(b['y'] for b in header_blocks))
        
        is_dual_column = False
        column_boundary = 0
        
        header_ys = []
        for y in header_y_values:
            same_row_headers = [b for b in header_blocks if abs(b['y'] - y) <= 15]
            if len(same_row_headers) >= 3:
                header_ys.append(y)
        
        if not header_ys:
            header_y = max(b['y'] for b in header_blocks)
        else:
            header_y = max(header_ys)
            
            all_header_texts = [b['text'] for b in header_blocks if abs(b['y'] - header_y) <= 15]
            from collections import Counter
            text_counts = Counter(all_header_texts)
            has_duplicate = any(count >= 2 for count in text_counts.values())
            
            if has_duplicate:
                for text, count in text_counts.items():
                    if count >= 2:
                        dup_blocks = [b for b in header_blocks if b['text'] == text and abs(b['y'] - header_y) <= 15]
                        dup_blocks.sort(key=lambda b: b['x'])
                        if len(dup_blocks) >= 2:
                            left_dup = dup_blocks[0]
                            right_dup = dup_blocks[1]
                            
                            same_row_all = [b for b in header_blocks if abs(b['y'] - header_y) <= 15]
                            left_headers = [b for b in same_row_all if b['x'] < right_dup['x']]
                            right_headers = [b for b in same_row_all if b['x'] >= right_dup['x']]
                            
                            if left_headers and right_headers:
                                left_max_x = max(b['x'] + b['w'] for b in left_headers)
                                right_min_x = min(b['x'] for b in right_headers)
                                if right_min_x - left_max_x > 50:
                                    is_dual_column = True
                                    column_boundary = left_max_x
                                    break
        
        data_blocks = [b for b in blocks if b['y'] > header_y + 10]
        
        rows = []
        for b in data_blocks:
            placed = False
            for row in rows:
                if abs(row['y'] - b['y']) <= 15:
                    row['blocks'].append(b)
                    placed = True
                    break
            if not placed:
                rows.append({'y': b['y'], 'blocks': [b]})
        
        rows.sort(key=lambda r: r['y'])
        
        if is_dual_column:
            left_rows = []
            right_rows = []
            for row in rows:
                left_blocks = sorted([b for b in row['blocks'] if b['x'] < column_boundary], key=lambda b: b['x'])
                right_blocks = sorted([b for b in row['blocks'] if b['x'] >= column_boundary], key=lambda b: b['x'])
                if left_blocks:
                    left_rows.append(left_blocks)
                if right_blocks:
                    right_rows.append(right_blocks)
            
            left_items = self._parse_column_rows(left_rows)
            right_items = self._parse_column_rows(right_rows)
            items = left_items + right_items
        else:
            all_rows = [sorted(row['blocks'], key=lambda b: b['x']) for row in rows]
            items = self._parse_column_rows(all_rows)
        
        return items

    def _parse_column_rows(self, rows: List[List[dict]]) -> List[dict]:
        """解析单栏的行数据，每行是按x坐标排序的文本块列表"""
        col_items = []
        current_item = None
        
        for row_blocks in rows:
            line_text = " ".join(b['text'].strip() for b in row_blocks if b['text'].strip())
            if not line_text:
                continue
            
            skip = False
            for stop_pattern in self.STOP_PATTERNS:
                if stop_pattern in line_text:
                    if current_item:
                        col_items.append(current_item)
                    return col_items
            
            is_new_item = False
            item_content = ""
            
            numbered_match = re.match(r"^(\d+)[．.、]\s*(.+)$", line_text)
            if numbered_match:
                rest = numbered_match.group(2)
                if re.match(r"^[\u4e00-\u9fa5*]", rest) or re.match(r"^[A-Za-z]+", rest):
                    is_new_item = True
                    item_content = rest
            else:
                num_match = re.match(r"^(\d+)\s+(.+)$", line_text)
                if num_match:
                    rest = num_match.group(2)
                    if re.match(r"^[\u4e00-\u9fa5*]", rest) or re.match(r"^[A-Za-z]+", rest):
                        is_new_item = True
                        item_content = rest
                else:
                    num_match2 = re.match(r"^(\d+)([\u4e00-\u9fa5*].*)$", line_text)
                    if num_match2:
                        is_new_item = True
                        item_content = num_match2.group(2)
            
            if is_new_item:
                if current_item:
                    col_items.append(current_item)
                current_item = {"code": "", "name": "", "result": "", "unit": "", "ref_range": "", "method": ""}
                self._parse_item_content(item_content, current_item)
            elif current_item:
                if re.search(r"[\d.]+[-~—–][\d.]+", line_text) or "<" in line_text or ">" in line_text:
                    current_item["ref_range"] += " " + line_text.strip()
                elif current_item["ref_range"]:
                    current_item["ref_range"] += " " + line_text.strip()
                elif current_item["name"] and not current_item["result"]:
                    current_item["name"] += " " + line_text.strip()
        
        if current_item:
            col_items.append(current_item)
        
        return col_items

    def _parse_item_content(self, content: str, item: dict):
        """解析单行项目内容
        
        格式1：PCT *降钙素原 (发光法) 0.886 ↑ ng/ml 0.000 -0.052 电化学发光法
        格式2：*甲型肝炎病毒IgM抗体 HAV-M 5.420 AU/mL 0-20 磁微粒化学发光法
        格式3：CMV-DNA定量 <4.000E2 copies/ml <4.0E+02 荧光定量PCR
        格式4：*丙肝抗体IgG(发光法) Anti-HCV 0.003阴性 S/CO 0.00-1.00 磁微粒化学发光法
        """
        content = content.strip()
        
        parts = content.split()
        if not parts:
            return
        
        item["code"] = ""
        item["name"] = ""
        item["result"] = ""
        item["unit"] = ""
        item["ref_range"] = ""
        item["method"] = ""
        
        num_parts = len(parts)
        result_idx = -1
        flag_part = ""
        
        for i in range(num_parts):
            part = parts[i]
            if part == "阴性" or part == "阳性":
                if result_idx == -1:
                    prev_part = parts[i-1] if i > 0 else ""
                    if re.search(r"[\d.]+", prev_part):
                        result_idx = i - 1
                        flag_part = part
                break
            
            if "<" in part or ">" in part:
                result_idx = i
                break
            
            numeric_match = re.search(r"([\d.]+(?:[Ee][+-]?\d+)?)", part)
            if numeric_match:
                prev_part = parts[i-1] if i > 0 else ""
                has_chinese_before = re.search(r"[\u4e00-\u9fa5]", prev_part)
                has_chinese_anywhere_before = any(re.search(r"[\u4e00-\u9fa5]", p) for p in parts[:i])
                
                if has_chinese_before or prev_part in ("阴性", "阳性") or has_chinese_anywhere_before:
                    result_idx = i
                    if "阴性" in part:
                        flag_part = "阴性"
                    if "阳性" in part:
                        flag_part = "阳性"
                    break
        
        if result_idx == -1:
            if num_parts >= 3:
                item["code"] = ""
                item["name"] = parts[0].replace("*", "").strip()
                item["result"] = parts[1]
                item["ref_range"] = " ".join(parts[2:])
            elif num_parts == 2:
                item["code"] = ""
                item["name"] = parts[0].replace("*", "").strip()
                item["result"] = parts[1]
            else:
                item["name"] = content.replace("*", "").strip()
            return
        
        name_parts = parts[:result_idx]
        result_part = parts[result_idx]
        after_parts = parts[result_idx + 1 :]
        
        code = ""
        name = ""
        for p in name_parts:
            if re.match(r"^[A-Za-z][A-Za-z0-9-]*$", p) and len(p) <= 15 and not re.search(r"[\u4e00-\u9fa5]", p):
                code = p
            else:
                name += " " + p
        
        item["code"] = code
        item["name"] = name.strip().replace("*", "")
        
        if re.match(r"^\d+[+-]$", result_part):
            item["result"] = result_part
        else:
            numeric_match = re.search(r"([\d.]+(?:[Ee][+-]?\d+)?)", result_part)
            if numeric_match:
                item["result"] = numeric_match.group(1)
            
            flag_match = re.search(r"([↑↓])", result_part)
            if flag_match:
                item["result"] += flag_match.group(1)
        
        if flag_part and "阴性" not in item["result"] and "阳性" not in item["result"]:
            item["result"] += flag_part
        
        unit = ""
        ref_range = ""
        method = ""
        
        for p in after_parts:
            if p in ("阴性", "阳性"):
                if not item["result"]:
                    item["result"] += p
                elif item["result"] in ("阴性", "阳性"):
                    ref_range += " " + p
                else:
                    ref_range += " " + p
                continue
            
            if p in ("↑", "↓"):
                item["result"] += p
                continue
            
            if re.match(r"^[\d.]+[-~—–][\d.]+$", p) or "<" in p or ">" in p:
                ref_range += " " + p
            elif re.match(r"^-?[\d.]+$", p):
                ref_range += " " + p
            elif re.search(r"[\u4e00-\u9fa5]{2,}", p) and not re.match(r"^[\d.]+[-~—–][\d.]+$", p):
                method += " " + p
            elif not unit and not re.search(r"[\u4e00-\u9fa5]{2,}", p) and not re.match(r"^[\d.]+$", p):
                unit = p
        
        item["unit"] = unit.replace("↑", "").replace("↓", "").strip()
        item["ref_range"] = ref_range.strip()
        item["method"] = method.strip()

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

    def _convert_to_parsed_results(self, items: List[dict], page_no: int) -> List[ParsedResult]:
        """转换为标准ParsedResult格式"""
        results = []
        for idx, item in enumerate(items):
            self._clean_item(item)
            name = item.get("name", "")
            if self._is_invalid_item(name):
                continue
            parsed = ParsedResult(
                raw_item_name=name,
                raw_value=item.get("result", "")
            )

            result_str = item.get("result", "")
            parsed.value_numeric = self._extract_numeric_value(result_str)
            parsed.unit = item.get("unit", "")
            parsed.reference_text = item.get("ref_range", "").strip()
            parsed.page_no = page_no
            parsed.code = item.get("code", "")

            parsed.flag = self._detect_abnormal(result_str, parsed.reference_text)

            results.append(parsed)

        return results

    def _extract_numeric_value(self, result_str: str) -> Optional[float]:
        """从结果字符串中提取数值"""
        match = re.search(r"([\d.]+(?:[Ee][+-]?\d+)?)", result_str)
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

        # 有数值结果或文本结果都算有效
        valid_count = sum(1 for r in report.results if r.value_numeric is not None or r.raw_value)
        return min(95.0, valid_count * 3.0)