import re

UNIT_PATTERN = r"(IU/mL|U/mL|ng/mL|pg/mL|[μu]mol/L|mmo[Ll]/L|g/L|mg/L|U/L|%)"

text = "μmol/L 58. 0--110.0"
print(f"测试文本: '{text}'")

if re.search(r"--|[-~—–≤≥]", text):
    ref_patterns = [
        r"(\d+[\d.\s]*--[\d.\s]+\d)",
        r"(\d+\.?\d*\s*[-~—–]\s*\d+\.?\d*)",
        r"([≤≥<>]\s*\d+\.?\d*)",
    ]
    ref_match = None
    for i, pattern in enumerate(ref_patterns):
        ref_match = re.search(pattern, text)
        if ref_match:
            print(f"模式{i+1}匹配: '{ref_match.group(1)}'")
            break
    if ref_match:
        ref_part = ref_match.group(1).replace(" ", "")
        print(f"去除空格后: '{ref_part}'")
        text = text[:ref_match.start()]
        print(f"剩余文本: '{text}'")
