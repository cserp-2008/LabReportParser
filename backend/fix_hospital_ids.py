import sqlite3
import requests

BASE_URL = "http://localhost:8000"

login_data = {"username": "admin", "password": "admin123"}
response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
if response.status_code != 200:
    print(f"登录失败: {response.text}")
    exit(1)

token = response.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

conn = sqlite3.connect('labreport.db')
c = conn.cursor()
c.execute('SELECT report_id, file_name FROM Report WHERE hospital_id=5')
reports = c.fetchall()
conn.close()

print(f"需要修复hospital_id=5的报告数: {len(reports)}")
print("=" * 80)

for report_id, file_name in reports:
    print(f"\n重新解析: {file_name}")
    reparse_response = requests.post(
        f"{BASE_URL}/api/v1/report/{report_id}/reparse",
        json={},
        headers=headers,
        timeout=120
    )
    
    if reparse_response.status_code == 200:
        data = reparse_response.json()
        result_count = data['data'].get('result_count', 0)
        print(f"   ✅ 成功！指标数: {result_count}")
    else:
        print(f"   ❌ 失败: {reparse_response.text}")

print("\n" + "=" * 80)
conn = sqlite3.connect('labreport.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM Report WHERE hospital_id=5')
count = c.fetchone()[0]
print(f"修复后仍引用hospital_id=5的报告数: {count}")

c.execute('SELECT report_id, file_name, hospital_id FROM Report WHERE hospital_id=5')
remaining = c.fetchall()
if remaining:
    print("\n仍有问题的报告:")
    for r in remaining:
        print(f"  {r}")

conn.close()
