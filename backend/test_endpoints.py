"""获取火山方舟Endpoint列表"""
import httpx

API_KEY = "d82024ee-bcc0-4452-bb76-0715fb85b611"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

def get_endpoints():
    client = httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30.0
    )
    
    print("测试 /endpoints...")
    try:
        response = client.get("/endpoints")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:2000]}")
    except Exception as e:
        print(f"失败: {e}")
    
    # 测试其他可能的路径
    print("\n测试 /v1/models...")
    try:
        response = client.get("/v1/models")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:1000]}")
    except Exception as e:
        print(f"失败: {e}")

if __name__ == "__main__":
    get_endpoints()