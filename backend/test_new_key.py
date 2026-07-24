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

print(f"API Key: {config.api_key[:4]}****{config.api_key[-4:]}")
print(f"base_url: {config.base_url}")
print(f"model_name: {config.model_name}")

client = httpx.Client(
    headers={"Authorization": f"Bearer {config.api_key}"},
    timeout=60.0
)

try:
    response = client.post(f"{config.base_url}/chat/completions", json={
        "model": config.model_name,
        "messages": [{"role": "user", "content": "你好"}],
        "max_tokens": 100
    })
    print(f"\n状态码: {response.status_code}")
    if response.status_code == 200:
        print("成功!")
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"回复: {content[:100]}")
    else:
        print(f"失败: {response.text[:500]}")
except Exception as e:
    print(f"异常: {e}")

db.close()
