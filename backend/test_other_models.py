import os, sys, httpx, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import AIConfig

engine = create_engine('sqlite:///labreport.db')
Session = sessionmaker(bind=engine)
db = Session()

config = db.query(AIConfig).filter(AIConfig.is_active == 1).first()
if not config:
    print("没有找到AI配置")
    sys.exit(1)

client = httpx.Client(
    headers={"Authorization": f"Bearer {config.api_key}"},
    timeout=30.0
)

# 尝试几个不同的模型
models_to_try = [
    "deepseek-v3-2-251201",
    "doubao-seed-2-1-pro-260628",
    "kimi-k2-250905",
    "glm-4-5-air-20250728",
]

for model in models_to_try:
    url = f"{config.base_url}/chat/completions"
    print(f"\n尝试模型: {model}")
    try:
        response = client.post(url, json={
            "model": model,
            "messages": [{"role": "user", "content": "你好"}],
            "max_tokens": 100
        })
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print("成功!")
            print(response.json())
            break
        else:
            print(f"失败: {response.text[:300]}")
    except Exception as e:
        print(f"异常: {e}")

db.close()
