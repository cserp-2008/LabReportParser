import os
import requests

BASE_URL = "http://localhost:8000"
LABREPORT_DIR = r'D:\private\CS\CS\LabReport'

login_data = {"username": "admin", "password": "admin123"}
response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
if response.status_code != 200:
    print(f"登录失败: {response.text}")
    exit(1)

token = response.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

unuploaded_files = [
    '2026-05-06乙型肝炎DNA定量.pdf',
    '2026-05-06乙肝五项.pdf',
    '2026-05-06脂肪酶.pdf',
    '2026-05-06血型+不规则抗体.pdf',
    '2026-05-06血培养双侧双瓶（2需氧+2厌氧）.pdf',
    '2026-05-11一般细菌培养及鉴定(腹水)屎肠球菌.pdf'
]

print(f'开始上传 {len(unuploaded_files)} 个文件...\n')

success_count = 0
failed_count = 0

for file_name in unuploaded_files:
    file_path = os.path.join(LABREPORT_DIR, file_name)
    
    if not os.path.exists(file_path):
        print(f'❌ 文件不存在: {file_name}')
        failed_count += 1
        continue
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_name, f, 'application/pdf')}
            response = requests.post(f"{BASE_URL}/api/v1/upload/file", files=files, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            result_count = data['data'].get('result_count', 0)
            hospital_name = data['data'].get('patient', {}).get('hospital_name', '未知')
            print(f'✅ {file_name}')
            print(f'   识别指标: {result_count} 个')
            print(f'   医院: {hospital_name}')
            success_count += 1
        elif response.status_code == 409:
            print(f'⚠️ {file_name} - 已存在')
            success_count += 1
        else:
            print(f'❌ {file_name} - 上传失败: {response.text}')
            failed_count += 1
    except Exception as e:
        print(f'❌ {file_name} - 异常: {str(e)}')
        failed_count += 1
    
    print()

print(f'\n上传完成！成功: {success_count}, 失败: {failed_count}')