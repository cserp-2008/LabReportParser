import re

test_cases = [
    "171.1 ↑ μmol/L 0. 0--5.0",
    "125.2 ↑ umol/L 0.0--19.0",
    "5900. 0--12200.0",
    "μmol/L 58. 0--110.0",
    "↓mmo1/L 22.0--30.0",
    "70.90↓ μmol/L 208.00--506.00",
    "357.4↑ μmol/L 3.0--22.0",
]

for text in test_cases:
    print(f"\n测试文本: '{text}'")
    
    ref_patterns = [
        r"(\d+\.?\d*\s+[-~—–]\s+\d+\.?\d*)",
        r"(\d+\.?\d*\s*[-~—–]\s*\d+\.?\d*)",
        r"([≤≥<>]\s*\d+\.?\d*)",
    ]
    
    for i, pattern in enumerate(ref_patterns):
        ref_match = re.search(pattern, text)
        if ref_match:
            print(f"  模式{i+1}匹配: '{ref_match.group(1)}'")
            ref_part = ref_match.group(1).replace(" ", "")
            print(f"  去除空格后: '{ref_part}'")

    simple_pattern = r"(\d+\s*[-~—–]\s*\d+\.?\d*)"
    ref_match = re.search(simple_pattern, text)
    if ref_match:
        print(f"  简单模式匹配: '{ref_match.group(1)}'")
    
    space_pattern = r"(\d+\.\s*\d+\s*[-~—–]\s*\d+\.?\d*)"
    ref_match = re.search(space_pattern, text)
    if ref_match:
        print(f"  空格模式匹配: '{ref_match.group(1)}'")
    
    dash_pattern = r"(\d+[\d.\s]*--[\d.\s]+\d)"
    ref_match = re.search(dash_pattern, text)
    if ref_match:
        print(f"  双破折号模式匹配: '{ref_match.group(1)}'")
