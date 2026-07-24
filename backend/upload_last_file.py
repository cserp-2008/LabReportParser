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

file_name = '2026-05-11一般细菌培养及鉴定(腹水)屎肠球菌.pdf'
file_path = os.path.join(LABREPORT_DIR, file_name)

if not os.path.exists(file_path):
    print(f'文件不存在: {file_path}')
    exit(1)

print(f'开始上传: {file_name}')
print(f'文件路径: {file_path}')
print(f'文件大小: {os.path.getsize(file_path)} bytes')

try:
    with open(file_path, 'rb') as f:
        files = {'file': (file_name, f, 'application/pdf')}
        response = requests.post(f"{BASE_URL}/api/v1/upload/file?overwrite=true", files=files, headers=headers)
    
    print(f'\nHTTP状态码: {response.status_code}')
    print(f'响应内容: {response.text}')
    
    if response.status_code == 200:
        data = response.json()
        code = data.get('code', 200)
        
        if code == 409:
            print(f'\n⚠️ 文件已存在（MD5重复）')
            print(f'   已存在报告ID: {data["data"].get("existing_report_id")}')
            print(f'   已存在文件名: {data["data"].get("existing_file_name")}')
            
            print('\n尝试使用URL参数overwrite=true强制覆盖上传...')
            with open(file_path, 'rb') as f:
                files = {'file': (file_name, f, 'application/pdf')}
                response2 = requests.post(
                    f"{BASE_URL}/api/v1/upload/file",
                    files=files,
                    headers=headers,
                    params={'overwrite': True}
                )
            
            print(f'HTTP状态码: {response2.status_code}')
            print(f'响应内容: {response2.text}')
            
            if response2.status_code == 200:
                data2 = response2.json()
                if data2.get('code') == 200:
                    report_id = data2['data'].get('report_id', '')
                    parse_result = data2['data'].get('parse_result', {})
                    result_count = parse_result.get('result_count', 0) if parse_result else 0
                    print(f'\n✅ 覆盖上传成功！')
                    print(f'   报告ID: {report_id}')
                    print(f'   识别指标: {result_count} 个')
                    
                    if result_count == 0 and report_id:
                        print('\n⚠️ 识别指标为0，尝试使用江苏省人民医院解析器重新解析...')
                        reparse_response = requests.post(
                            f"{BASE_URL}/api/v1/report/{report_id}/reparse",
                            json={"parser_code": "jph"},
                            headers=headers
                        )
                        print(f'重新解析响应: {reparse_response.text}')
                        if reparse_response.status_code == 200:
                            reparse_data = reparse_response.json()
                            new_count = reparse_data['data'].get('result_count', 0)
                            print(f'✅ 重新解析成功！识别指标: {new_count} 个')
                else:
                    print(f'\n❌ 覆盖上传仍失败，code: {data2.get("code")}')
        elif code == 200:
            report_id = data['data'].get('report_id', '')
            parse_result = data['data'].get('parse_result', {})
            result_count = parse_result.get('result_count', 0) if parse_result else 0
            print(f'\n✅ 上传成功！')
            print(f'   报告ID: {report_id}')
            print(f'   识别指标: {result_count} 个')
            
            if result_count == 0 and report_id:
                print('\n⚠️ 识别指标为0，尝试重新解析...')
                reparse_response = requests.post(
                    f"{BASE_URL}/api/v1/report/{report_id}/reparse",
                    json={"parser_code": "jph"},
                    headers=headers
                )
                print(f'重新解析响应: {reparse_response.text}')
        else:
            print(f'\n❌ 上传失败，code: {code}')
    else:
        print(f'\n❌ 上传失败，HTTP状态码: {response.status_code}')
except Exception as e:
    print(f'\n❌ 异常: {str(e)}')

print('\n验证上传结果...')
import sqlite3
conn = sqlite3.connect('labreport.db')
c = conn.cursor()
c.execute('SELECT report_id, file_name, hospital_id, is_delete FROM report WHERE file_name=?', (file_name,))
result = c.fetchone()
if result:
    print(f'数据库中记录: {result}')
else:
    print('数据库中未找到该文件记录')
c.execute('SELECT COUNT(*) FROM report WHERE is_delete=0')
total = c.fetchone()[0]
print(f'数据库中未删除报告总数: {total}')
conn.close()
