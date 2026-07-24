"""医院名称识别模块

从 PDF 提取的文本中识别医院名称。
基于关键词匹配，支持后续扩展为 YAML 模板配置。
"""
import re
from typing import Optional, List

# 常见医院关键词模式
HOSPITAL_PATTERNS = [
    r"([\u4e00-\u9fa5]{2,20}医院)",
    r"([\u4e00-\u9fa5]{2,20}卫生院)",
    r"([\u4e00-\u9fa5]{2,20}医学检验[中心所])",
    r"([\u4e00-\u9fa5]{2,20}体检中心)",
    r"([\u4e00-\u9fa5]{2,20}人民医院)",
    r"([\u4e00-\u9fa5]{2,20}大学附属[\u4e00-\u9fa5]*医院)",
    r"([\u4e00-\u9fa5]{2,20}中心医院)",
    r"([\u4e00-\u9fa5]{2,20}妇幼保健院)",
    r"([\u4e00-\u9fa5]{2,20}中医院)",
    r"([\u4e00-\u9fa5]{2,20}第二医院)",
    r"([\u4e00-\u9fa5]{2,20}第三医院)",
    r"([\u4e00-\u9fa5]{2,20}第一医院)",
]


class HospitalDetector:
    """医院名称识别器"""

    # 医院名称映射：处理简称、别名、代码等
    HOSPITAL_ALIASES = {
        "人民医院": "江苏省人民医院",
        "省人民医院": "江苏省人民医院",
        "省人医": "江苏省人民医院",
        "JPH": "江苏省人民医院",
        "南京医科大学第一附属医院": "江苏省人民医院",
        "南医大一附院": "江苏省人民医院",
        "明基医院": "南京明基医院",
        "南京市第二医院": "南京市第二医院",
        "市第二医院": "南京市第二医院",
        "肝病医院": "南京市第二医院",
    }

    def detect(self, text: str) -> Optional[str]:
        """从文本中识别医院名称

        Args:
            text: PDF 提取的全文

        Returns:
            医院名称，未识别返回 None
        """
        if not text:
            return None

        candidates = []
        for pattern in HOSPITAL_PATTERNS:
            match = re.search(pattern, text)
            if match:
                name = match.group(1)
                if 4 <= len(name) <= 30:
                    candidates.append(name)

        if not candidates:
            for alias, full_name in self.HOSPITAL_ALIASES.items():
                if alias in text:
                    return full_name
            return None

        candidates.sort(key=len, reverse=True)
        
        for name in candidates:
            if "明基" in name:
                return "南京明基医院"
            if "江苏省人民医院" in name or "人民医院" in name:
                return "江苏省人民医院"
            if "南京医科大学附属" in name:
                return "江苏省人民医院"
            if "南京市第二医院" in name or "第二医院" in name:
                return "南京市第二医院"

        for name in candidates:
            for alias, full_name in self.HOSPITAL_ALIASES.items():
                if alias in name:
                    return full_name

        return candidates[0]

    def detect_from_lines(self, lines: List[str]) -> Optional[str]:
        """从前几行文本识别医院（通常医院名在页眉）"""
        head_lines = lines[:10] if len(lines) >= 10 else lines
        return self.detect("\n".join(head_lines))
