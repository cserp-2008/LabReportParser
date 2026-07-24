import sqlite3
import requests
import time

BASE_URL = "http://localhost:8000"

print("登录系统...")
login_data = {"username": "admin", "password": "admin123"}
response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
if response.status_code != 200:
    print(f"登录失败: {response.text}")
    exit(1)

token = response.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("登录成功！")

conn = sqlite3.connect('labreport.db')
c = conn.cursor()
c.execute("SELECT report_id, file_name FROM Report WHERE is_delete=0 AND hospital_id IS NULL")
reports = c.fetchall()
conn.close()

print(f"\n需要指定医院的报告数: {len(reports)}")
print("全部使用江苏省人民医院(ID=2)重新解析")
print("=" * 80)

success_count = 0
failed_count = 0

for idx, (report_id, file_name) in enumerate(reports):
    try:
        print(f"\n[{idx+1}/{len(reports)}] {file_name}")
        
        reparse_response = requests.post(
            f"{BASE_URL}/api/v1/report/{report_id}/reparse",
            json={"hospital_id": 2},
            headers=headers,
            timeout=120
        )
        
        if reparse_response.status_code == 200:
            data = reparse_response.json()
            result_count = data['data'].get('result_count', 0)
            success_count += 1
            print(f"   ✅ 成功！指标数: {result_count}")
        else:
            failed_count += 1
            print(f"   ❌ 失败: {reparse_response.text}")
            
        time.sleep(0.2)
        
    except Exception as e:
        failed_count += 1
        print(f"   ❌ 异常: {str(e)}")

print("\n" + "=" * 80)
print(f"重新解析完成！成功: {success_count}, 失败: {failed_count}")

print("\n验证最终状态...")
conn = sqlite3.connect('labreport.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM Report WHERE is_delete=0 AND hospital_id IS NULL")
null_hospital = c.fetchone()[0]
print(f"医院未识别的报告数: {null_hospital}")
conn.close()
