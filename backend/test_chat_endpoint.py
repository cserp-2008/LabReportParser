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

print(f"base_url: {config.base_url}")

# 使用完整URL测试
client = httpx.Client(
    headers={"Authorization": f"Bearer {config.api_key}"},
    timeout=30.0
)

# 尝试不同的完整URL
urls = [
    f"{config.base_url}/chat/completions",
    f"{config.base_url}/v1/chat/completions",
]

for url in urls:
    print(f"\n尝试: {url}")
    try:
        response = client.post(url, json={
            "model": "qwen3-8b-20250429",
            "messages": [{"role": "user", "content": "你好"}],
            "max_tokens": 100
        })
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print("成功!")
            print(response.json())
            break
        else:
            print(f"失败: {response.text[:500]}")
    except Exception as e:
        print(f"异常: {e}")

db.close()
