# LabReportParser V3.0

医学检验报告智能解析与管理系统

## 项目简介

LabReportParser 是一个企业级医学检验报告解析管理系统，支持 PDF、图片化验单批量上传、自动 OCR 识别、多医院报告统一标准化、数据入库、溯源预览、指标趋势分析、人工校对等功能。

## 技术栈

### 后端
- Python 3.12
- FastAPI 0.115
- SQLAlchemy 2.0
- SQLite（默认，可切换 MySQL 8.0）
- PyMuPDF（PDF 渲染）
- pdfplumber（文字层提取）
- PaddleOCR（扫描件 OCR 识别）
- python-jose（JWT 鉴权）
- openpyxl（Excel 导出）

### 前端
- Vue 3 + TypeScript
- Element Plus
- Pinia
- Vue Router
- Axios
- ECharts

## 快速开始

### 环境要求
- Python 3.12 + Node.js 18
- PaddleOCR 首次运行会自动下载模型
- 默认使用 SQLite，无需额外数据库配置

### Docker 部署（推荐）

1. 克隆项目
```bash
cd d:\private\CS\CS\src
```

2. 启动所有服务
```bash
docker-compose up -d
```

3. 访问应用
- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

4. 默认账号
- 用户名: admin
- 密码: admin123

### 本地开发

#### 后端
```bash
cd backend
pip install -r requirements.txt
# 首次启动会自动创建 SQLite 数据库并初始化基础数据
python main.py
# 服务启动于 http://localhost:8000
```

启动后可访问：
- 健康检查：`GET http://localhost:8000/health`
- API 文档：`http://localhost:8000/docs`

#### 前端
```bash
cd frontend
npm install
npm run dev
```

## 项目结构

```
.
├── backend/              # 后端项目
│   ├── api/             # API 路由
│   │   ├── auth.py      # 认证登录、获取当前用户
│   │   ├── upload.py    # 文件上传（自动触发解析）
│   │   ├── report.py    # 报告列表、详情、删除
│   │   ├── review.py    # 人工复核、审计日志
│   │   ├── trend.py     # 趋势分析
│   │   ├── stats.py     # 仪表盘统计
│   │   ├── export.py    # CSV / Excel 导出
│   │   ├── task.py      # 任务管理、重新解析
│   │   └── preview.py   # PDF 预览
│   ├── core/            # 配置、安全、Schema
│   ├── db/              # 数据库模型与会话
│   ├── parser/          # 解析引擎
│   │   ├── pdf_parser.py        # PDF 提取 + OCR 回退
│   │   ├── lab_result_parser.py # 检验结果解析
│   │   ├── hospital_detector.py # 医院名称识别
│   │   ├── standardizer.py      # 指标标准化映射
│   │   └── service.py           # 解析调度服务
│   ├── storage/         # 上传文件存储
│   ├── main.py          # 入口文件
│   ├── requirements.txt
│   └── labreport.db     # SQLite 数据库（自动生成）
├── frontend/             # 前端项目
│   ├── src/
│   │   ├── views/       # 页面组件
│   │   │   ├── Login.vue       # 登录
│   │   │   ├── Layout.vue      # 主框架
│   │   │   ├── Dashboard.vue   # 仪表盘
│   │   │   ├── Upload.vue      # 上传中心
│   │   │   ├── Reports.vue     # 报告列表
│   │   │   ├── ReportDetail.vue# 报告详情与复核
│   │   │   └── Trend.vue       # 趋势分析图表
│   │   ├── api/         # 接口封装
│   │   ├── router/      # 路由配置
│   │   ├── store/       # Pinia 状态管理
│   │   └── utils/       # Axios 请求封装
│   └── package.json
├── sql/                  # 数据库脚本
├── storage/              # 文件存储根目录
└── docker-compose.yml
```

## 功能特性

### 文件上传与解析
- ✅ 支持 PDF、JPG、PNG、BMP、TIF 等格式上传
- ✅ 单文件 / 多文件批量上传，带上传进度显示
- ✅ 文字 PDF 直接使用 pdfplumber 提取文字层
- ✅ 扫描版 PDF 自动回退到 PyMuPDF 渲染 + PaddleOCR 识别
- ✅ 上传后自动触发解析流程

### 检验结果解析
- ✅ 自动提取患者信息（姓名、性别、年龄、采样时间、报告时间）
- ✅ 提取检验指标（项目名、数值、单位、参考范围、异常标记）
- ✅ OCR 噪声行过滤（医院名、页码、章节标记等）
- ✅ 质量评分（0-100 分，依据完整度计算）
- ✅ 自动识别医院名称并关联

### 指标标准化
- ✅ 检验项目别名映射到标准项目（17 个标准项目）
- ✅ 支持模糊匹配（包含关系）
- ✅ 清理项目名干扰字符

### 报告管理
- ✅ 报告列表（分页、按文件名/患者搜索）
- ✅ 报告详情（患者信息 + 检验指标 + 预览）
- ✅ 报告删除（软删除，带审计日志）

### 人工复核
- ✅ 修改检验指标数值、异常标记
- ✅ 操作审计日志（记录前后值）
- ✅ 审计日志查询

### 趋势分析
- ✅ 按检验项目查看历史趋势
- ✅ ECharts 折线图，标注最大最小值
- ✅ 上升/下降/平稳趋势自动判断

### 数据导出
- ✅ CSV 格式导出
- ✅ Excel 格式导出（openpyxl）

### 仪表盘
- ✅ 总报告数、待复核数、本月上传、异常指标数统计

### 任务管理
- ✅ 上传任务列表
- ✅ 任务详情查询
- ✅ 失败报告一键重新解析

### 系统特性
- ✅ JWT 鉴权 + RBAC 角色权限
- ✅ 首次启动自动建表与种子数据初始化（管理员账号、角色、标准检验项目）
- ✅ CORS 跨域支持
- ✅ API 文档自动生成（Swagger UI）

## 核心解析流程

```
PDF 文件
   ↓
[文字层提取] pdfplumber
   ↓ 有效字符 < 10？
[是] PyMuPDF 渲染为图片 → PaddleOCR 识别
   ↓
合并全文文本
   ↓
┌──────────────┬──────────────┬──────────────┐
│ 患者信息提取  │ 检验指标提取  │ 医院名称识别  │
└──────────────┴──────────────┴──────────────┘
   ↓
[指标标准化] 别名 → 标准项目映射
   ↓
写入数据库 + 计算质量分
   ↓
返回解析结果
```

## 主要 API 接口

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 认证 | POST | `/api/v1/auth/login` | 登录获取 Token |
| 认证 | GET | `/api/v1/auth/me` | 获取当前用户 |
| 上传 | POST | `/api/v1/upload/file` | 上传单个文件并自动解析 |
| 报告 | GET | `/api/v1/report/list` | 报告列表 |
| 报告 | GET | `/api/v1/report/{id}` | 报告详情 |
| 报告 | DELETE | `/api/v1/report/{id}` | 删除报告 |
| 复核 | PUT | `/api/v1/review/{id}` | 修改检验指标 |
| 复核 | GET | `/api/v1/review/audit-logs` | 审计日志 |
| 趋势 | GET | `/api/v1/trend/items` | 检验项目列表 |
| 趋势 | GET | `/api/v1/trend/analysis/{id}` | 趋势分析数据 |
| 统计 | GET | `/api/v1/stats/dashboard` | 仪表盘统计 |
| 导出 | GET | `/api/v1/export/csv` | CSV 导出 |
| 导出 | GET | `/api/v1/export/excel` | Excel 导出 |
| 任务 | GET | `/api/v1/task/list` | 任务列表 |
| 任务 | POST | `/api/v1/task/reparse/{id}` | 重新解析报告 |
| 健康 | GET | `/health` | 健康检查 |

## 解析效果示例

对扫描版生化检验报告 PDF 的解析效果：

- 提取检验指标数：**22 项**
- 质量评分：**91.82**
- 患者姓名：**陈松**（正确识别）
- 自动识别医院、采样时间、各指标参考范围与异常标记

## 许可证

MIT
