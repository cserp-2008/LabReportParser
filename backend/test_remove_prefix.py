import re

test_cases = [
    "ALT丙氨酸氨基转移酶",
    "AST天门冬氨酸氨基转移酶",
    "UREA尿素",
    "CREA肌酐",
    "LDH乳酸脱氢酶",
    "GLU葡萄糖",
    "AMY淀粉酶",
    "CK肌酸激酶",
    "TBIL总胆红素",
    "ALP碱性磷酸酶",
    "GGT谷氨酰转肽酶",
    "CHE胆碱脂酶",
    "Ca钙",
    "K钾",
    "Na钠",
    "CL氯",
    "Mg镁",
    "P磷",
    "白蛋白",
    "总胆红素",
    "葡萄糖",
]

print("测试去除英文简称前缀:")
print("=" * 60)

for name in test_cases:
    cleaned = re.sub(r"^[A-Z][A-Za-z0-9/\-._]*\s*", "", name).strip()
    print(f"{name:<20} → {cleaned}")
