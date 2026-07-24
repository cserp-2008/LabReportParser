"""测试完整URL调用"""
import httpx

API_KEY = "d82024ee-bcc0-4452-bb76-0715fb85b611"

def test_full_url():
    # 测试完整URL，不带base_url前缀
    print("测试完整URL: https://ark.cn-beijing.volces.com/api/v3/chat/completions")
    try:
        response = httpx.post(
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "doubao-seed-2-1-pro-260628",
                "messages": [{"role": "user", "content": "hello"}],
                "max_tokens": 10
            },
            timeout=30.0
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
    except Exception as e:
        print(f"失败: {e}")

if __name__ == "__main__":
    test_full_url()