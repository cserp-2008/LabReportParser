import os, sys, httpx, json

api_key = "sk-ebriqqqmiwanzlfpztkegzzniryzedaewqlvmakoezxxkbtp"

platforms = [
    {"name": "火山方舟", "base_url": "https://ark.cn-beijing.volces.com/api/v3", "model": "doubao-seed-2-1-pro-260628"},
    {"name": "OpenAI", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    {"name": "豆包API", "base_url": "https://api.doubao.com/v1", "model": "doubao-seed-2-1-pro-260628"},
    {"name": "通义千问", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen3-8b"},
    {"name": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    {"name": "智谱AI", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4"},
]

client = httpx.Client(timeout=60.0)

for platform in platforms:
    print(f"\n=== 尝试: {platform['name']} ===")
    print(f"base_url: {platform['base_url']}")
    print(f"model: {platform['model']}")
    
    try:
        response = client.post(
            f"{platform['base_url']}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": platform["model"],
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 100
            }
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print("成功!")
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"回复: {content[:100]}")
            print(f"\n找到可用平台: {platform['name']}")
            print(f"base_url: {platform['base_url']}")
            print(f"model: {platform['model']}")
            break
        else:
            msg = response.text[:200]
            print(f"失败: {msg}")
    except Exception as e:
        print(f"异常: {e}")
