"""API 测试脚本

测试 LabReportParser 后端所有核心接口。
"""
import requests
import os
import sys
import json

BASE_URL = "http://localhost:8000"
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "report", "2026", "07")

passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} {detail}")


def main():
    token = None

    # 1. 健康检查
    print("\n=== 1. 健康检查 ===")
    r = requests.get(f"{BASE_URL}/health")
    test("GET /health", r.status_code == 200 and r.json().get("status") == "healthy", r.text)

    # 2. 登录
    print("\n=== 2. 登录 ===")
    r = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "username": "admin", "password": "admin123"
    })
    data = r.json()
    test("POST /auth/login", r.status_code == 200 and data.get("code") == 0, r.text)
    if data.get("data"):
        token = data["data"]["access_token"]
        print(f"  Token: {token[:40]}...")

    if not token:
        print("登录失败，无法继续测试")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    # 3. 获取当前用户
    print("\n=== 3. 获取当前用户 ===")
    r = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    data = r.json()
    test("GET /auth/me", data.get("code") == 0 and data["data"]["username"] == "admin", r.text)

    # 4. 获取趋势项目列表
    print("\n=== 4. 获取检验项目列表 ===")
    r = requests.get(f"{BASE_URL}/api/v1/trend/items", headers=headers)
    data = r.json()
    items = data.get("data", [])
    test("GET /trend/items", data.get("code") == 0 and len(items) > 0, f"items={len(items)}")
    if items:
        print(f"  检验项目数: {len(items)}, 首项: {items[0]}")

    # 5. 上传 PDF 文件并解析
    print("\n=== 5. 上传 PDF 文件并自动解析 ===")
    pdf_files = []
    if os.path.exists(STORAGE_DIR):
        for f in os.listdir(STORAGE_DIR):
            if f.endswith(".pdf"):
                pdf_files.append(os.path.join(STORAGE_DIR, f))

    uploaded_report_id = None
    if pdf_files:
        test_file = pdf_files[0]
        print(f"  上传文件: {os.path.basename(test_file)}")
        with open(test_file, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/api/v1/upload/file",
                files={"file": (os.path.basename(test_file), f, "application/pdf")},
                headers=headers,
            )
        data = r.json()
        test("POST /upload/file", data.get("code") == 0, r.text)
        if data.get("data"):
            uploaded_report_id = data["data"]["report_id"]
            parse_result = data["data"].get("parse_result", {})
            print(f"  报告ID: {uploaded_report_id}")
            print(f"  解析结果: 指标数={parse_result.get('result_count', 0)}, "
                  f"质量分={parse_result.get('quality_score', 0)}, "
                  f"患者={parse_result.get('patient_name', '未知')}")
            test("解析成功 (result_count > 0)", parse_result.get("result_count", 0) > 0,
                 f"result_count={parse_result.get('result_count')}")
    else:
        print("  未找到测试 PDF 文件，跳过上传测试")

    # 6. 获取报告列表
    print("\n=== 6. 获取报告列表 ===")
    r = requests.get(f"{BASE_URL}/api/v1/report/list", headers=headers, params={"page": 1, "page_size": 10})
    data = r.json()
    test("GET /report/list", data.get("code") == 0, r.text)
    report_list = data.get("data", {}).get("list", [])
    print(f"  报告总数: {data.get('data', {}).get('total', 0)}")
    if report_list:
        report_id = report_list[0]["report_id"]
        print(f"  首个报告: {report_list[0].get('file_name')}, 质量分={report_list[0].get('quality_score')}")

        # 7. 获取报告详情
        print("\n=== 7. 获取报告详情 ===")
        r = requests.get(f"{BASE_URL}/api/v1/report/{report_id}", headers=headers)
        data = r.json()
        test("GET /report/{id}", data.get("code") == 0, r.text)
        detail = data.get("data", {})
        results = detail.get("results", [])
        print(f"  检验结果数: {len(results)}")
        if results:
            print(f"  首条指标: {results[0].get('raw_item_name')}={results[0].get('raw_value')}{results[0].get('unit', '')}")
        test("报告详情有检验结果", len(results) > 0, f"results={len(results)}")

        # 8. 人工复核 - 修改指标
        print("\n=== 8. 人工复核 - 修改检验指标 ===")
        if results:
            result_id = results[0]["result_id"]
            r = requests.put(f"{BASE_URL}/api/v1/review/{result_id}", headers=headers, json={
                "raw_value": "999",
                "flag": "↑",
            })
            data = r.json()
            test("PUT /review/{id}", data.get("code") == 0, r.text)

        # 9. 趋势分析
        print("\n=== 9. 趋势分析 ===")
        r = requests.get(f"{BASE_URL}/api/v1/trend/analysis/1", headers=headers)
        data = r.json()
        test("GET /trend/analysis/{item_id}", data.get("code") == 0, r.text)

    # 10. 仪表盘统计
    print("\n=== 10. 仪表盘统计 ===")
    r = requests.get(f"{BASE_URL}/api/v1/stats/dashboard", headers=headers)
    data = r.json()
    test("GET /stats/dashboard", data.get("code") == 0, r.text)
    if data.get("data"):
        stats = data["data"]
        print(f"  总报告: {stats.get('total')}, 待复核: {stats.get('pending')}, "
              f"本月: {stats.get('monthly')}, 异常: {stats.get('abnormal')}")

    # 11. 任务列表
    print("\n=== 11. 任务列表 ===")
    r = requests.get(f"{BASE_URL}/api/v1/task/list", headers=headers, params={"page": 1, "page_size": 10})
    data = r.json()
    test("GET /task/list", data.get("code") == 0, r.text)
    tasks = data.get("data", {}).get("list", [])
    print(f"  任务总数: {data.get('data', {}).get('total', 0)}")

    # 12. 审计日志
    print("\n=== 12. 审计日志 ===")
    r = requests.get(f"{BASE_URL}/api/v1/review/audit-logs", headers=headers, params={"page": 1, "page_size": 10})
    data = r.json()
    test("GET /review/audit-logs", data.get("code") == 0, r.text)
    logs = data.get("data", {}).get("list", [])
    print(f"  审计日志数: {data.get('data', {}).get('total', 0)}")

    # 13. CSV 导出
    print("\n=== 13. CSV 导出 ===")
    r = requests.get(f"{BASE_URL}/api/v1/export/csv", headers=headers)
    test("GET /export/csv", r.status_code == 200 and "csv" in r.headers.get("content-type", ""), r.text[:100])
    print(f"  导出内容大小: {len(r.content)} bytes")

    # 14. Excel 导出
    print("\n=== 14. Excel 导出 ===")
    r = requests.get(f"{BASE_URL}/api/v1/export/excel", headers=headers)
    test("GET /export/excel", r.status_code == 200 and "spreadsheet" in r.headers.get("content-type", ""), r.text[:100])
    print(f"  导出内容大小: {len(r.content)} bytes")

    # 汇总
    print(f"\n{'='*50}")
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print(f"{'='*50}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
