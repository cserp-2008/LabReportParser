"""检验结果解析模块

从 PDF 提取的文本中解析检验指标数据。
提取字段：项目名称、数值、单位、参考范围、异常标记、患者信息、采样时间。
依据设计说明书 2.1.4 检验指标标准化需求。
"""
import re
from typing import List, Optional, Dict
from dataclasses import dataclass, field


@dataclass
class ParsedResult:
    """单条检验结果"""
    raw_item_name: str
    raw_value: str
    value_numeric: Optional[float] = None
    unit: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    reference_text: Optional[str] = None
    flag: Optional[str] = None
    page_no: int = 1
    bbox_left: Optional[int] = None
    bbox_top: Optional[int] = None
    bbox_right: Optional[int] = None
    bbox_bottom: Optional[int] = None
    ocr_confidence: float = 95.0


@dataclass
class ParsedReport:
    """解析后的报告"""
    patient_name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[str] = None
    sample_time: Optional[str] = None
    report_time: Optional[str] = None
    hospital_name: Optional[str] = None
    results: List[ParsedResult] = field(default_factory=list)
    quality_score: float = 0.0


class LabResultParser:
    """检验结果解析器"""

    # 患者姓名模式
    NAME_PATTERNS = [
        r"姓名[:：\s]*([\u4e00-\u9fa5]{2,4})",
        r"患者姓名[:：\s]*([\u4e00-\u9fa5]{2,4})",
        r"姓\s*名\s*([\u4e00-\u9fa5]{2,4})",
    ]

    # 性别模式
    GENDER_PATTERNS = [
        r"性别[:：\s]*([男女])",
        r"性\s*别\s*([男女])",
    ]

    # 年龄模式
    AGE_PATTERNS = [
        r"年龄[:：\s]*(\d{1,3}\s*岁?)",
        r"年\s*龄\s*(\d{1,3}\s*岁?)",
        r"年龄[:：\s]*(\d{1,3})",
    ]

    # 采样时间模式（支持日期和时间之间无分隔的情况，如 OCR 输出 2026-01-0708:23:58）
    # "采集时间"和"采样时间"是同一个意思
    SAMPLE_TIME_PATTERNS = [
        r"采样时间[:：\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
        r"采集时间[:：\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
        r"标本采集时间[:：\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
        r"送检日期[:：\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
        r"采集日期[:：\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
        r"采样日期[:：\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
        r"标本时间[:：\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
    ]

    # 报告时间模式
    REPORT_TIME_PATTERNS = [
        r"报告日期[:：\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
        r"报告时间[:：\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
        r"审核日期[:：\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{1,2}:\d{1,2}(?::\d{1,2})?)",
    ]

    # 数值行匹配：项目名 + 数值 + 单位 + 参考范围 + 标记
    # 格式示例: 白细胞计数 6.5 10^9/L 3.5-9.5
    # 格式示例: 谷丙转氨酶 45 ↑ U/L 0-40
    # 格式示例: WBC 6.5 10^9/L 3.5-9.5

    # 参考范围模式: 3.5-9.5 或 3.5~9.5 或 <40 或 ≥1.0
    REF_RANGE_PATTERN = r"([\d.]+)\s*[-~]\s*([\d.]+)"

    # 异常标记
    FLAG_PATTERN = r"[↑↓↑↓<>]"

    def parse(self, text: str, page_no: int = 1) -> ParsedReport:
        """解析全文，提取患者信息和检验结果"""
        report = ParsedReport()

        if not text:
            return report

        # 提取患者信息
        report.patient_name = self._extract_first(text, self.NAME_PATTERNS)
        report.gender = self._extract_first(text, self.GENDER_PATTERNS)
        report.age = self._extract_first(text, self.AGE_PATTERNS)
        report.sample_time = self._extract_first(text, self.SAMPLE_TIME_PATTERNS)
        report.report_time = self._extract_first(text, self.REPORT_TIME_PATTERNS)

        # 提取检验结果
        report.results = self._parse_lab_results(text, page_no)

        # 计算质量分
        report.quality_score = self._calculate_quality_score(report)

        return report

    def _extract_first(self, text: str, patterns: List[str]) -> Optional[str]:
        """用多个模式尝试提取，返回第一个匹配结果"""
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def _parse_lab_results(self, text: str, page_no: int) -> List[ParsedResult]:
        """从文本行中解析检验结果

        化验单常见格式：
        项目名称      结果    单位    参考范围    标记
        白细胞计数    6.5     10^9/L  3.5-9.5
        谷丙转氨酶    45      U/L     0-40       ↑
        """
        results = []
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue

            result = self._parse_line(line, page_no)
            if result:
                results.append(result)

        return results

    def _parse_line(self, line: str, page_no: int) -> Optional[ParsedResult]:
        """解析单行文本，尝试提取检验结果

        匹配逻辑：
        1. 行中必须包含一个数值（可能带小数）
        2. 项目名在数值前面
        3. 数值后可能有单位、参考范围、异常标记
        """
        # 跳过明显非数据行（标题、表头、患者信息等）
        skip_keywords = ["姓名", "性别", "年龄", "采样", "报告", "送检", "审核",
                         "医院", "样本", "标本", "编号", "科室", "床号", "门诊",
                         "住院", "临床诊断", "检验项目", "结果", "单位", "参考",
                         "提示", "序号", "备注", "说明", "签发", "检验师",
                         "审核者", "采集者", "日期", "时间", "页码",
                         "检验报告", "生化", "彩超", "心电图", "条码",
                         "病人", "病人号", "病人类型", "检验仪器",
                         "送检", "标本", "申请", "诊断"]
        for kw in skip_keywords:
            if kw in line and not self._has_numeric_value(line):
                return None

        # 跳过含章节标记的行（如 【生化】）
        if "【" in line or "】" in line:
            return None
        
        # 跳过 (cid: 开头的行（PDF解析遗留的CID引用）
        if line.startswith("(cid:"):
            return None

        # 跳过含页码标识的行（如 第1页/共1页）
        if re.search(r"第\s*\d+\s*页|共\s*\d+\s*页", line):
            return None

        # 跳过由大量单字空格分隔的行（OCR 噪声，通常是医院名称等）
        # 如 "南 京 明 基 医 院"
        segments = line.split()
        if len(segments) >= 4 and all(len(s) == 1 for s in segments[:4]):
            return None

        # 匹配数值：整数或小数（可能带负号），不能纯在参考范围中
        # 常见格式：项目名 数值 单位 参考范围 标记
        # 提取数值模式
        numeric_match = re.search(r"(?<![\d.-])(-?\d+\.?\d*)(?!\d*\s*[-~]\s*\d)", line)

        if not numeric_match:
            return None

        value_str = numeric_match.group(1)
        try:
            value_numeric = float(value_str)
        except ValueError:
            return None

        # 过滤不合理的数值（如年份、页码等）
        if value_numeric > 100000 or value_numeric < -10000:
            return None
        # 过滤看起来像年份的值
        if 1900 < value_numeric < 2100 and "." not in value_str:
            return None

        # 提取项目名：数值前面的文本
        prefix = line[:numeric_match.start()].strip()
        # 去除常见前缀符号
        prefix = re.sub(r"^[•·\-\d.、\s]+", "", prefix).strip()
        # 清理项目名中的多余空格
        item_name = prefix.strip()

        if not item_name or len(item_name) > 50:
            return None

        # 跳过纯数字项目名
        if re.match(r"^[\d\s]+$", item_name):
            return None

        # 跳过明显非项目名的行
        if len(item_name) < 1:
            return None

        # 清理项目名称：去除(干化学法)和前缀字母/符号
        item_name = item_name.replace("*", "")
        item_name = item_name.replace("△", "")
        item_name = item_name.replace("＊", "")
        item_name = re.sub(r"[（\(]干化学法[）\)]", "", item_name)
        item_name = re.sub(r"[（\(][^）\)]+[）\)]", "", item_name)
        item_name = re.sub(r"^[A-Z][A-Za-z0-9/\-._]*\s*[%#]?\s*", "", item_name)
        item_name = re.sub(r"^[A-Za-z0-9/\-._]+\s+[*△＊]?\s*", "", item_name)
        item_name = re.sub(r"^[A-Za-z0-9/\-._]+[\s]*[*△＊]+\s*", "", item_name)
        item_name = re.sub(r"^-\s*", "", item_name)
        item_name = re.sub(r"^eGFR\s*", "", item_name)
        item_name = re.sub(r"^CMV-DNA\s*", "", item_name)
        item_name = re.sub(r"^EB-?DNA\s*", "", item_name)
        item_name = re.sub(r"^EB病毒\s*", "", item_name)
        item_name = re.sub(r"^COBAS\s*", "", item_name)
        item_name = re.sub(r"^D-Dime\s*", "", item_name)
        item_name = re.sub(r"^PCR\s*", "", item_name)
        item_name = re.sub(r"^typing\s+[a-zA-Z]+\s*", "", item_name)
        item_name = re.sub(r"^Phagocyte-ST\s*", "", item_name)
        item_name = re.sub(r"^PIVKA-\s*", "", item_name)
        item_name = re.sub(r"^MALB(?:/[a-zA-Z]+)?\s*", "", item_name)
        item_name = re.sub(r"^u-TP(?:/[a-zA-Z]+)?\s*", "", item_name)
        item_name = re.sub(r"^hs-[a-zA-Z]+\s*", "", item_name)
        item_name = re.sub(r"^hs[CR]+\s*", "", item_name)
        item_name = re.sub(r"^TPOAB\s*", "", item_name)
        item_name = re.sub(r"^TNF-\s*", "", item_name)
        item_name = re.sub(r"^TSH\s*\*\s*", "", item_name)
        item_name = re.sub(r"^UCREA\s*", "", item_name)
        item_name = re.sub(r"^UCB\s*", "", item_name)
        item_name = re.sub(r"^NEUT%\s*", "", item_name)
        item_name = re.sub(r"^LYMPH%\s*", "", item_name)
        item_name = re.sub(r"^EO#\s*", "", item_name)
        item_name = re.sub(r"^N端-前脑钠肽\s*", "", item_name)
        item_name = re.sub(r"^C-Ca\s*", "", item_name)
        item_name = re.sub(r"^-3-β-D-\s*", "", item_name)
        item_name = re.sub(r"^Y-\s*", "", item_name)
        item_name = re.sub(r"^Ca\s*", "", item_name)
        
        item_name = re.sub(r"^>\s*[\d.]+\s*", "", item_name)
        item_name = re.sub(r"^<\s*[\d.]+\s*", "", item_name)
        
        if re.match(r"^α-羟丁酸脱氢酶\s+[\d]", item_name):
            item_name = "α-羟丁酸脱氢酶"
        elif re.match(r"^β2微球蛋白\s+[\d]", item_name):
            item_name = "β2微球蛋白"
        
        item_name = re.sub(r"\s+", " ", item_name).strip()

        if not item_name or len(item_name) < 1:
            return None

        # 跳过项目名中仍含明显非项目关键字的情况
        non_item_keywords = ["医院", "科室", "姓名", "页", "条码", "仪器",
                             "病人", "采样", "报告", "审核", "送检",
                             "性别", "年龄", "诊断", "标本", "床号",
                             "申请", "临床", "类型", "住院", "地址：",
                             "检测结果可能受", "具体数值：", "鉴定结果：",
                             "样本号", "备注", "注：", "采集时间", "报告时间",
                             "接收时间", "检验备注", "女：晨尿：", "附见：",
                             "腹腔内见", "荧光定量PCR", "王敏", "PCR"]
        for kw in non_item_keywords:
            if kw in item_name:
                return None

        # 提取异常标记
        flag = None
        suffix = line[numeric_match.end():].strip()
        if "↑" in suffix or "↑" in line:
            flag = "↑"
        elif "↓" in suffix or "↓" in line:
            flag = "↓"
        elif "H" in suffix.split() or "h" in suffix.split():
            flag = "↑"
        elif "L" in suffix.split() or "l" in suffix.split():
            flag = "↓"

        # 提取单位：数值后的文本中，参考范围前的部分
        unit = None
        ref_low = None
        ref_high = None
        ref_text = None

        # 尝试匹配参考范围 X-Y
        ref_match = re.search(r"([\d.]+)\s*[-~]\s*([\d.]+)", suffix)
        if ref_match:
            try:
                ref_low = float(ref_match.group(1))
                ref_high = float(ref_match.group(2))
            except ValueError:
                pass

            # 单位在数值和参考范围之间
            between = suffix[:ref_match.start()].strip()
            # 去掉异常标记
            between = re.sub(r"[↑↓<>]", "", between).strip()
            # 去掉多余空格
            between = between.strip()
            if between and len(between) <= 15:
                unit = between
        else:
            # 尝试匹配文本参考范围 如 <7.0 或 阴性
            text_ref_match = re.search(r"(阴性|阳性|[-<≥≤>]\s*[\d.]+)", suffix)
            if text_ref_match:
                ref_text = text_ref_match.group(1)
                between = suffix[:text_ref_match.start()].strip()
                between = re.sub(r"[↑↓<>]", "", between).strip()
                if between and len(between) <= 15:
                    unit = between
            else:
                # 没有参考范围，尝试提取单位
                # 单位通常紧跟数值后
                unit_match = re.match(
                    r"^\s*([a-zA-Zμ×⁹¹²/^\d.%↓↑\-≤≥<>]+\s*[a-zA-Zμ×⁹¹²/^\d.%]*)",
                    suffix,
                )
                if unit_match:
                    candidate = unit_match.group(1).strip()
                    # 清理异常标记
                    candidate = re.sub(r"[↑↓<>]", "", candidate).strip()
                    if candidate and 1 <= len(candidate) <= 15:
                        unit = candidate

        result = ParsedResult(
            raw_item_name=item_name,
            raw_value=value_str,
            value_numeric=value_numeric,
            unit=unit,
            reference_low=ref_low,
            reference_high=ref_high,
            reference_text=ref_text,
            flag=flag,
            page_no=page_no,
            ocr_confidence=95.0,
        )

        return result

    def _has_numeric_value(self, line: str) -> bool:
        """检查行中是否有数值"""
        return bool(re.search(r"\d+\.?\d*", line))

    def _calculate_quality_score(self, report: ParsedReport) -> float:
        """计算报告质量分（0-100）

        依据：指标完整度 + 患者信息完整度
        """
        score = 60.0  # 基础分

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
            # 有参考范围的结果占比
            has_ref = sum(1 for r in report.results if r.reference_low is not None)
            if report.results:
                ref_ratio = has_ref / len(report.results)
                score += ref_ratio * 10
        else:
            score = 0.0

        return min(score, 100.0)
