"""检查存储目录中的报告文件"""
import os

storage_dir = '../storage/report'
count = 0
for root, dirs, files in os.walk(storage_dir):
    for f in files:
        if f.endswith('.pdf'):
            count += 1
            print(f"  {os.path.join(root, f)}")
print(f"\n共 {count} 个PDF文件")
