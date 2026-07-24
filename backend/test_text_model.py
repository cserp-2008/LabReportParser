"""测试文本模型识别化验单"""
import httpx
import json

API_KEY = "d82024ee-bcc0-4452-bb76-0715fb85b611"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL = "doubao-seed-2-1-pro-260628"

TEST_TEXT = """【生化】 南 京 明 基 医 院 苏HR 第1页/共1页
检验仪器：生化仪CobasC8000 检验报告单 条码号：160107585082
南京医科大学附属明基医院
姓名：陈松 科室：心血管内科 标本：血清
病人号：303590271 床号：病人类型：门诊 采样时间：2026-01-0708:23:58
性别：男 年龄：52岁 诊断：高胆固醇血症 接收时间：2026-01-0708:26:02
代号项目名称 结果 提示单位 参考范围 代号 项目名称 结果 提示单位 参考范围
GA 糖化白蛋白 13.3 11--16 APO-A1*载脂蛋白A1 1. 73 g/L 1. 04-2. 02
IBIL 间接胆红素 11. 73 umol/L 0--19 APO-B*载脂蛋白B 1.88 g/L 0.66--1.33
ALT *谷丙转氨酶 42.50 U/L 9--50 UREA *尿素 8.59 mmol/L 3. 1--8.0
AST *谷草转氨酶 33.20 U/L 15-—40 CREA *肌酐 90 umol/L 57--97
GGT *谷氨酰转肽酶 20 U/L 10--60 UA *尿酸 423.0 umol/L 202.3--416.5
ALP *碱性磷酸酶 47 U/L 45-125 GLU *葡萄糖 8.19 mmol/L 3.89--6.11
TP *总蛋白 79.30 g/L 65--85 K *钾 5.12 mmol/L 3.5--5.3
ALB *白蛋白 52.40 g/L 40--55 NA *钠 140 mmol/L 137--147
LDH *乳酸脱氢酶 146. 7 U/L 120-250 CL *氯 100 mmol/L 99--110
TBIL *总胆红素 16.80 umol/L 0--26 Ca *钙 2.51 mmol/L 2.11--2.52
CK *肌酸激酶 116. 0 U/L 50--310 P *磷 1. 13 mmol/L 0.85--1.51
DBIL *直接胆红素 5. 07 umol/L ≤8 AMY *淀粉酶 178 U/L 35--135
C02-L*血清碳酸氢盐 29.2 mmol/L 22.0--29.0
CHOL *总胆固醇 7.98 mmol/L <5.17
TG *甘油三酯 1. 88 mmol/L<2.26 A/G 白蛋白与球蛋白比值1.95 1. 2-2. 4
HDL-C*高密度脂蛋白 1. 35 mmol/L 1. 00--3.10 GLOB 球蛋白 26.90 g/L 20--30
LDL-C*低密度脂蛋白 5.88 mmol/L 低危人群：<3.4；中高危人群：<2.6；极高危人群：<1.8；超高危人群：<1.4
申请医生：房艳红 报告时间：2026-01-0709:34:19"""

PROMPT = """你是一个专业的医疗化验单识别助手。请仔细阅读化验单文本内容，并提取所有检验指标数据。

要求：
1. 识别患者信息：姓名、性别、年龄、采集时间、报告时间、医院名称
2. 识别所有检验项目，每项包含：项目名称、缩写(如有)、结果值、单位、参考范围、异常标记(↑↓等)
3. 结果必须是严格的JSON格式，不要包含任何其他文字或Markdown格式
4. 如果某项数据缺失，对应字段设为null

JSON格式示例：
{
  "patient": {
    "name": "张三",
    "gender": "男",
    "age": "35岁",
    "sample_time": "2026-05-08 10:30",
    "report_time": "2026-05-08 14:00",
    "hospital": "江苏省人民医院"
  },
  "items": [
    {
      "name": "白细胞计数",
      "code": "WBC",
      "result": "7.5",
      "unit": "×10⁹/L",
      "ref_range": "4.0-10.0",
      "flag": null
    }
  ]
}

请直接返回JSON，不要有任何解释或额外文字！"""

def test_text_recognition():
    client = httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=120.0
    )
    
    messages = [
        {
            "role": "user",
            "content": f"{PROMPT}\n\n化验单文本内容如下，请提取数据：\n\n{TEST_TEXT}"
        }
    ]
    
    print(f"测试模型: {MODEL}")
    print("正在调用AI...")
    
    try:
        response = client.post(
            "/chat/completions",
            json={
                "model": MODEL,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "max_tokens": 8000,
                "temperature": 0.1
            }
        )
        response.raise_for_status()
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        print("\nAI返回:")
        print(content)
        
        try:
            ai_result = json.loads(content)
            print(f"\n患者姓名: {ai_result.get('patient', {}).get('name')}")
            print(f"识别指标数: {len(ai_result.get('items', []))}")
            for item in ai_result.get('items', [])[:5]:
                print(f"  {item.get('code', '')} {item.get('name', '')} = {item.get('result', '')} {item.get('unit', '')} ref={item.get('ref_range', '')}")
        except json.JSONDecodeError:
            print("JSON解析失败")
            
    except Exception as e:
        print(f"调用失败: {e}")

if __name__ == "__main__":
    test_text_recognition()