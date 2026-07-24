import re

unit_patterns = [
    r"(IU/mL|U/mL|ng/mL|pg/mL|μmol/L|mmol/L|g/L|mg/L|U/L|%)",
    r"(COI|NT-proBNP|fL|pg|10°/L|1012/L|1/n)",
]

test_cases = [
    "μmol/L 58. 0--110.0",
    "umol/L 0.0--19.0",
    "mmo1/L 22.0--30.0",
    "mmol/L",
]

for text in test_cases:
    print(f"\n测试文本: '{text}'")
    for i, pattern in enumerate(unit_patterns):
        match = re.search(pattern, text)
        if match:
            print(f"  模式{i+1}匹配: '{match.group(1)}'")
        else:
            print(f"  模式{i+1}不匹配")
