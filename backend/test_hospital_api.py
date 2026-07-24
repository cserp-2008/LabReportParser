import requests

BASE_URL = "http://localhost:8000"

login_data = {"username": "admin", "password": "admin123"}
response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)

if response.status_code == 200:
    data = response.json()
    token = data["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    hospital_response = requests.get(f"{BASE_URL}/api/v1/hospital/list", headers=headers)
    print(f"医院列表API状态码: {hospital_response.status_code}")
    print(f"医院列表响应: {hospital_response.text}")