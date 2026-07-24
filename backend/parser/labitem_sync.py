"""标准指标库自动同步服务

从已解析的 LabResult 中学习指标信息，自动扩充/更新标准指标库 LabItem。

同步策略：
1. 新增：报告中出现但标准库中不存在的指标，自动创建 LabItem + Alias
2. 补全：已存在但 reference_range 为空的标准指标，从报告中最常见的参考范围填充
3. 单位：已存在但 standard_unit 为空的标准指标，从报告中最常见的单位填充

调用时机：
- 服务启动时（_init_seed_data 之后）
- 报告解析完成后
- 管理员手动触发（API）
"""
import re
import logging
from collections import Counter
from typing import Optional, Tuple, Dict

from sqlalchemy.orm import Session
from sqlalchemy import func

from db.models import LabItem, Alias, LabResult

logger = logging.getLogger(__name__)


class LabItemSync:
    """标准指标库自动同步器"""

    # 无效的指标名（OCR噪声、空值、太短等）
    INVALID_NAMES = {
        "", "none", "null", "na", "n/a", "项目名称", "简称", "结果", "单位",
        "参考范围", "参考值", "中文名称", "代号", "序号",
    }

    # 名称中包含这些关键词的视为噪声，不创建指标
    NOISE_KEYWORDS = [
        "样本号", "采集时间", "接收时间", "检验门诊", "门诊信息", "送检",
        "危人群", "低危人群", "中危人群", "高危人群", "晨尿", "报告时间",
        "检验师", "审核", "打印", "备注", "结论", "建议",
    ]

    # 常见单位列表，用于从 raw_item_name 中剥离单位
    COMMON_UNITS = [
        "umol/L", "μmol/L", "mmo1/L", "mmol/L", "g/L", "mg/L", "IU/L", "U/L",
        "ng/ml", "pg/ml", "mg/dL", "fL", "pg", "×10⁹/L", "×10¹²/L",
        "10^9/L", "10^12/L", "%", "mmol/l", "umol/l", "uIU/ml",
    ]

    def __init__(self, db: Session):
        self.db = db
        self._alias_map: Optional[Dict[str, int]] = None
        self._item_map: Optional[Dict[int, LabItem]] = None

    def _load_mappings(self):
        """加载现有别名映射（惰性）"""
        if self._alias_map is not None:
            return
        self._alias_map = {}
        self._item_map = {}
        for item in self.db.query(LabItem).all():
            self._item_map[item.item_id] = item
            if item.item_name:
                self._alias_map[item.item_name.lower()] = item.item_id
            if item.abbr:
                self._alias_map[item.abbr.lower()] = item.item_id
        for alias in self.db.query(Alias).all():
            self._alias_map[alias.alias_name.lower()] = alias.item_id

    def _split_code_name(self, raw_name: str) -> Tuple[str, str]:
        """从 raw_item_name 中分离代号和项目名称

        处理形如 "ALT *谷丙转氨酶"、"IBIL 间接胆红素"、
        "ALP *△碱性磷酸酶"、"HBDH *△α-羟丁酸脱氢酶"、
        "LP (a) * 脂蛋白 (a)" 的输入。

        Returns:
            (code, name): 代号和清理后的名称
        """
        if not raw_name:
            return "", ""

        text = raw_name.strip()
        # 去除前后的标记符号 * △ ▲ #
        text = text.lstrip("*△▲#")

        # 尝试匹配 "代号 名称" 或 "代号*名称" 格式
        # 代号通常是大写字母/数字/斜杠/括号组合，名称以中文或希腊字母开头
        # 分隔符可以是 * △ ▲ 空格 的组合（如 "*△"、" * "）
        m = re.match(
            r"^([A-Z][A-Z0-9/\-._()\s]{0,15}?)\s*[*△▲\s]+\s*([\u4e00-\u9fa5αβγ].*)$",
            text,
        )
        if m:
            code = m.group(1).strip()
            name = m.group(2).strip()
            # 确保代号确实是代号（不含中文）且至少2个字符
            if not re.search(r"[\u4e00-\u9fa5]", code) and len(code) >= 2:
                return code, name

        # 纯中文名称，去除残留标记
        name = re.sub(r"^[*△▲#\s]+", "", text)
        # 去除尾部单位
        for unit in self.COMMON_UNITS:
            if name.endswith(" " + unit) or name.endswith(unit):
                name = name[: -len(unit)].rstrip()
                break

        return "", name.strip()

    def _is_valid_name(self, name: str) -> bool:
        """检查名称是否有效"""
        if not name or len(name) < 2:
            return False
        if name.lower() in self.INVALID_NAMES:
            return False
        # 包含噪声关键词
        for kw in self.NOISE_KEYWORDS:
            if kw in name:
                return False
        # 以 "<" 或 "≤" 开头（如 "<3.4" 被误当作名称）
        if re.match(r"^[<≤≥>]", name):
            return False
        # 必须包含至少一个中文字符或希腊字母
        if not re.search(r"[\u4e00-\u9fa5αβγ]", name):
            return False
        # 全数字或全是符号
        if re.match(r"^[\d\s.\-+/<>≤≥↑↓*,]+$", name):
            return False
        # 包含日期（如 "采集时间：2026-05-07" 残留）
        if re.search(r"\d{4}-\d{2}-\d{2}", name):
            return False
        # 包含时间（如 ":57:28"）
        if re.search(r":\d{2}:\d{2}", name):
            return False
        return True

    def _find_item_by_raw(self, raw_name: str) -> Optional[LabItem]:
        """通过标准化映射查找 LabItem"""
        self._load_mappings()
        if not raw_name:
            return None

        normalized = raw_name.strip().lower()

        # 精确匹配
        item_id = self._alias_map.get(normalized)
        if item_id:
            return self._item_map.get(item_id)

        # 清理后匹配
        _, name = self._split_code_name(raw_name)
        if name:
            item_id = self._alias_map.get(name.lower())
            if item_id:
                return self._item_map.get(item_id)

        # 模糊匹配（包含关系）
        for alias_key, iid in self._alias_map.items():
            if not alias_key or len(alias_key) < 2:
                continue
            if alias_key in normalized or normalized in alias_key:
                return self._item_map.get(iid)

        return None

    def _most_common_value(self, values) -> str:
        """取最常见的非空值"""
        counter = Counter(v for v in values if v and v.strip())
        if not counter:
            return ""
        return counter.most_common(1)[0][0]

    def _normalize_ref_range(self, ref: str) -> str:
        """规范化参考范围字符串"""
        if not ref:
            return ""
        ref = ref.strip()
        # 去除单位残留（如 "9-50 U/L" -> "9-50"）
        for unit in self.COMMON_UNITS:
            ref = re.sub(r"\s+" + re.escape(unit) + r"$", "", ref, flags=re.IGNORECASE)
        # 去除数字间的空格（如 "5. 46--16.2" -> "5.46-16.2"、"0. 00--6. 90" -> "0.00-6.90"）
        ref = re.sub(r"(\d)\.\s+(\d)", r"\1.\2", ref)
        ref = re.sub(r"(\d)\s+(\d)", r"\1\2", ref)
        # 去除多余的 "-"（如 "0--10" -> "0-10"）
        ref = re.sub(r"-{2,}", "-", ref)
        # 去除尾部空格和符号
        ref = ref.rstrip(" -")
        return ref.strip()

    def _fix_unit_ref(self, unit: str, ref: str) -> Tuple[str, str]:
        """修复被OCR错误切分的单位和参考范围

        例如：
            unit="73 umol/L 0-", ref="-19"  ->  unit="umol/L", ref="0-19"
            unit="U/L 10-", ref="-60"        ->  unit="U/L", ref="10-60"
            unit="g/L 65-", ref="-85"        ->  unit="g/L", ref="65-85"
        """
        if not unit:
            return unit, ref

        unit = unit.strip()
        ref = (ref or "").strip()

        # 检查 unit 中是否混入了参考范围的左半部分（如 "umol/L 0-" 或 "U/L 10-"）
        # 模式: <真正单位> <数字>-  后面 ref 是 -<数字>
        m = re.match(
            r"^(.*?)\s+(\d+\.?\d*)\s*[-—–]$",
            unit,
        )
        if m:
            real_unit = m.group(1).strip()
            ref_low = m.group(2)
            # 从 ref 中提取上限（如 "-19" -> "19"）
            ref_high_match = re.match(r"^[-—–]\s*(\d+\.?\d*)", ref)
            if ref_high_match:
                ref_high = ref_high_match.group(1)
                return real_unit, f"{ref_low}-{ref_high}"

        # 检查 unit 开头是否混入了结果数值（如 "73 umol/L 0-" 中的 "73"）
        # 模式: <数字> <真正单位> ...
        m = re.match(r"^\d+\.?\d*\s+(.+)$", unit)
        if m:
            return self._fix_unit_ref(m.group(1), ref)

        return unit, ref

    def sync(self) -> Dict:
        """执行同步，返回同步统计

        Returns:
            {
                "new_items": 新增的标准指标数,
                "new_aliases": 新增的别名数,
                "updated_ref": 更新参考范围的指标数,
                "updated_unit": 更新单位的指标数,
                "scanned_results": 扫描的 LabResult 数,
            }
        """
        self._load_mappings()

        # 统计每个 raw_item_name 对应的单位和参考范围
        rows = self.db.query(
            LabResult.raw_item_name,
            LabResult.unit,
            LabResult.reference_text,
        ).filter(LabResult.raw_item_name.isnot(None)).all()

        stats = {
            "new_items": 0,
            "new_aliases": 0,
            "updated_ref": 0,
            "updated_unit": 0,
            "scanned_results": len(rows),
        }

        # 按 raw_item_name 分组统计
        grouped: Dict[str, Dict[str, list]] = {}
        for raw_name, unit, ref_text in rows:
            if not raw_name or not raw_name.strip():
                continue
            key = raw_name.strip()
            if key not in grouped:
                grouped[key] = {"units": [], "refs": []}
            if unit:
                grouped[key]["units"].append(unit)
            if ref_text:
                grouped[key]["refs"].append(ref_text)

        # 遍历每个原始指标名
        for raw_name, data in grouped.items():
            existing = self._find_item_by_raw(raw_name)

            if existing:
                # 已存在：检测并修复被OCR错误切分的 unit/ref
                raw_ref = self._most_common_value(data["refs"])
                raw_unit = self._most_common_value(data["units"])
                fixed_unit, fixed_ref = self._fix_unit_ref(raw_unit, raw_ref)
                fixed_ref = self._normalize_ref_range(fixed_ref)

                # 修复错误的 unit（仅修复明显被污染的单位：包含空格或纯数字）
                if existing.standard_unit and fixed_unit and existing.standard_unit != fixed_unit:
                    old_unit = existing.standard_unit.strip()
                    # 仅当单位明显异常时才修复：包含空格（混入了其他内容）或纯数字（不是有效单位）
                    is_corrupted = (" " in old_unit) or re.match(r"^[\d.\-]+$", old_unit)
                    if is_corrupted:
                        logger.info(
                            f"修复单位: {existing.item_name} "
                            f"'{existing.standard_unit}' -> '{fixed_unit}'"
                        )
                        existing.standard_unit = fixed_unit

                # 修复错误的 reference_range
                if existing.reference_range and fixed_ref and existing.reference_range != fixed_ref:
                    # 当前 ref 以 "-" 开头（被截断的右半部分）
                    if re.match(r"^[-—–]\s*\d", existing.reference_range):
                        logger.info(
                            f"修复参考范围: {existing.item_name} "
                            f"'{existing.reference_range}' -> '{fixed_ref}'"
                        )
                        existing.reference_range = fixed_ref

                # 补全空的参考范围
                if not existing.reference_range and fixed_ref:
                    existing.reference_range = fixed_ref
                    stats["updated_ref"] += 1
                    logger.debug(f"补全参考范围: {existing.item_name} -> {fixed_ref}")

                # 补全空的单位
                if not existing.standard_unit and fixed_unit:
                    existing.standard_unit = fixed_unit
                    stats["updated_unit"] += 1
                    logger.debug(f"补全单位: {existing.item_name} -> {fixed_unit}")

                # 为已有指标添加新别名（如果 raw_name 与 item_name 不同）
                if raw_name.lower() != existing.item_name.lower():
                    existing_alias = self._alias_map.get(raw_name.lower())
                    if not existing_alias:
                        self.db.add(Alias(
                            item_id=existing.item_id,
                            alias_name=raw_name,
                        ))
                        self._alias_map[raw_name.lower()] = existing.item_id
                        stats["new_aliases"] += 1
            else:
                # 不存在：新增 LabItem
                code, name = self._split_code_name(raw_name)
                if not self._is_valid_name(name):
                    continue

                # 再次用清理后的名称查找（避免重复创建）
                existing_after_clean = self._alias_map.get(name.lower())
                if existing_after_clean:
                    # 添加 raw_name 作为别名
                    self.db.add(Alias(
                        item_id=existing_after_clean,
                        alias_name=raw_name,
                    ))
                    self._alias_map[raw_name.lower()] = existing_after_clean
                    stats["new_aliases"] += 1
                    continue

                # 创建新 LabItem
                raw_unit = self._most_common_value(data["units"])
                raw_ref = self._most_common_value(data["refs"])
                fixed_unit, fixed_ref = self._fix_unit_ref(raw_unit, raw_ref)
                fixed_ref = self._normalize_ref_range(fixed_ref)
                unit = fixed_unit or None
                ref = fixed_ref or None

                # 根据 abbr 推断分类
                category = self._guess_category(name, code)

                new_item = LabItem(
                    item_name=name,
                    abbr=code or None,
                    english_name=None,
                    category=category,
                    standard_unit=unit,
                    reference_range=ref,
                    description="自动从报告中学习",
                )
                self.db.add(new_item)
                self.db.flush()

                # 创建别名
                self.db.add(Alias(
                    item_id=new_item.item_id,
                    alias_name=raw_name,
                ))
                if code and code.lower() != name.lower():
                    self.db.add(Alias(
                        item_id=new_item.item_id,
                        alias_name=code,
                    ))

                # 更新内存映射
                self._item_map[new_item.item_id] = new_item
                self._alias_map[name.lower()] = new_item.item_id
                self._alias_map[raw_name.lower()] = new_item.item_id
                if code:
                    self._alias_map[code.lower()] = new_item.item_id

                stats["new_items"] += 1
                logger.info(
                    f"新增标准指标: {name} (abbr={code}, unit={unit}, ref={ref})"
                )

        self.db.commit()
        logger.info(
            f"LabItem 同步完成: 新增指标 {stats['new_items']} 个, "
            f"新增别名 {stats['new_aliases']} 个, "
            f"补全参考范围 {stats['updated_ref']} 个, "
            f"补全单位 {stats['updated_unit']} 个"
        )
        return stats

    def _guess_category(self, name: str, code: str) -> str:
        """根据名称/代号猜测分类"""
        text = (name + " " + code).lower()
        rules = [
            (("白细胞", "wbc", "中性粒", "淋巴", "单核", "嗜酸", "嗜碱", "血小板", "plt", "rbc", "红细胞", "血红蛋白", "hgb", "hct", "mcv", "mch", "mchc", "rdw", "pdw", "mpv", "血常规"), "血常规"),
            (("转氨酶", "alt", "ast", "胆红素", "bil", "蛋白", "alb", "tp", "球蛋白", "glob", "白球比", "a/g", "碱性磷酸酶", "alp", "谷氨酰", "ggt", "乳酸脱氢酶", "ldh", "胆汁酸", "tba", "胆碱酯酶", "肝功能"), "肝功能"),
            (("肌酐", "cr", "尿素", "bun", "urea", "尿酸", "ua", "肾小球滤过", "egfr", "胱抑素", "cysc", "β2微球蛋白", "β2-mg", "肾功能"), "肾功能"),
            (("血糖", "glu", "fbg", "糖化", "hba1c", "胰岛素", "ins", "c肽", "c-p", "血糖"), "血糖"),
            (("胆固醇", "chol", "tc", "甘油三酯", "tg", "hdl", "ldl", "脂蛋白", "载脂蛋白", "apo", "血脂"), "血脂"),
            (("钾", "k+", "钠", "na+", "氯", "cl-", "钙", "ca", "磷", "phos", "镁", "mg", "铁", "fe", "电解质"), "电解质"),
            (("t3", "t4", "tsh", "ft3", "ft4", "甲状腺", "tpoab", "tgab", "甲状腺功能"), "甲状腺"),
            (("凝血", "pt", "aptt", "inr", "fib", "d-二聚体", "d-dimer", "fdp", "at", "凝血功能"), "凝血功能"),
            (("乙肝", "hbsag", "hbsab", "hbeag", "hbeab", "hbcab", "丙肝", "hcv", "hiv", "梅毒", "传染病"), "传染病"),
            (("尿", "尿微量白蛋白", "malb", "尿总蛋白", "u-tp", "尿肌酐", "ucr", "尿"), "尿常规"),
        ]
        for keywords, category in rules:
            if any(kw in text for kw in keywords):
                return category
        return "其他"
