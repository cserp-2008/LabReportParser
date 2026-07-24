CREATE DATABASE IF NOT EXISTS LabReport DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE LabReport;

-- 医院表
CREATE TABLE IF NOT EXISTS Hospital (
    hospital_id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_name VARCHAR(200) NOT NULL,
    province VARCHAR(50),
    city VARCHAR(50),
    parser_code VARCHAR(100) NOT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 上传任务表
CREATE TABLE IF NOT EXISTS UploadTask (
    task_id VARCHAR(64) PRIMARY KEY,
    user_id INT NOT NULL,
    file_total INT DEFAULT 0,
    success_count INT DEFAULT 0,
    fail_count INT DEFAULT 0,
    status TINYINT COMMENT '0待处理 1处理中 2完成 3失败',
    progress FLOAT DEFAULT 0,
    message TEXT,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    finish_time DATETIME NULL
) ENGINE=InnoDB;

-- 报告主表
CREATE TABLE IF NOT EXISTS Report (
    report_id VARCHAR(64) PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    hospital_id INT NULL,
    patient_name VARCHAR(50),
    gender VARCHAR(10),
    age VARCHAR(20),
    sample_time DATETIME,
    report_time DATETIME,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    file_size BIGINT,
    file_md5 VARCHAR(64) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    thumbnail_path VARCHAR(500),
    page_count INT DEFAULT 1,
    quality_score FLOAT,
    review_status TINYINT DEFAULT 0 COMMENT '0未复核 1已复核 2人工修改',
    is_delete TINYINT DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task(task_id),
    INDEX idx_hospital(hospital_id),
    INDEX idx_md5(file_md5),
    INDEX idx_sample_time(sample_time)
) ENGINE=InnoDB;

-- 报告页表
CREATE TABLE IF NOT EXISTS ReportPage (
    page_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    report_id VARCHAR(64) NOT NULL,
    page_no INT NOT NULL,
    preview_image_path VARCHAR(500),
    width INT,
    height INT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_report(report_id)
) ENGINE=InnoDB;

-- OCR文本块
CREATE TABLE IF NOT EXISTS OCRBlock (
    block_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    page_id BIGINT NOT NULL,
    text TEXT NOT NULL,
    confidence FLOAT,
    bbox_left INT,
    bbox_top INT,
    bbox_right INT,
    bbox_bottom INT,
    INDEX idx_page(page_id)
) ENGINE=InnoDB;

-- 标准检验项目
CREATE TABLE IF NOT EXISTS LabItem (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(100) NOT NULL,
    abbr VARCHAR(50),
    english_name VARCHAR(200),
    category VARCHAR(50),
    standard_unit VARCHAR(30),
    description TEXT
) ENGINE=InnoDB;

-- 指标别名
CREATE TABLE IF NOT EXISTS Alias (
    alias_id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NOT NULL,
    alias_name VARCHAR(100) NOT NULL,
    INDEX idx_item(item_id)
) ENGINE=InnoDB;

-- 检验结果核心表
CREATE TABLE IF NOT EXISTS LabResult (
    result_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    report_id VARCHAR(64) NOT NULL,
    page_id BIGINT NOT NULL,
    item_id INT NULL,
    raw_item_name VARCHAR(100) NOT NULL,
    raw_value VARCHAR(100),
    value_numeric DECIMAL(18,4) NULL,
    unit VARCHAR(30),
    reference_low DECIMAL(18,4) NULL,
    reference_high DECIMAL(18,4) NULL,
    reference_text VARCHAR(200),
    flag VARCHAR(10) COMMENT '↑ ↓ 正常',
    bbox_left INT,
    bbox_top INT,
    bbox_right INT,
    bbox_bottom INT,
    ocr_confidence FLOAT,
    review_status TINYINT DEFAULT 0,
    source_file VARCHAR(255) NOT NULL,
    source_path VARCHAR(500) NOT NULL,
    INDEX idx_report(report_id),
    INDEX idx_item(item_id),
    INDEX idx_page(page_id)
) ENGINE=InnoDB;

-- 用户表
CREATE TABLE IF NOT EXISTS User (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(200) NOT NULL,
    real_name VARCHAR(50),
    is_enable TINYINT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 角色表
CREATE TABLE IF NOT EXISTS Role (
    role_id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    permission_list TEXT
) ENGINE=InnoDB;

-- 用户角色关联
CREATE TABLE IF NOT EXISTS UserRole (
    user_id INT NOT NULL,
    role_id INT NOT NULL,
    PRIMARY KEY(user_id, role_id)
) ENGINE=InnoDB;

-- 审计日志表
CREATE TABLE IF NOT EXISTS AuditLog (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    operate_user_id INT,
    operate_type VARCHAR(30) NOT NULL,
    target_table VARCHAR(50) NOT NULL,
    target_id VARCHAR(64) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    operate_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(50),
    INDEX idx_target(target_table, target_id),
    INDEX idx_time(operate_time)
) ENGINE=InnoDB;

-- 初始化默认用户 (admin/admin123)
INSERT INTO User (username, password, real_name) VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyNUzV5j.XcG', '系统管理员');

-- 初始化默认角色
INSERT INTO Role (role_name, permission_list) VALUES ('admin', '["*"]');
INSERT INTO Role (role_name, permission_list) VALUES ('user', '["report:view", "report:upload", "result:view"]');

-- 关联用户角色
INSERT INTO UserRole (user_id, role_id) VALUES (1, 1);

-- 初始化标准检验项目
INSERT INTO LabItem (item_name, abbr, english_name, category, standard_unit) VALUES
('白细胞计数', 'WBC', 'White Blood Cell', '血常规', '×10⁹/L'),
('红细胞计数', 'RBC', 'Red Blood Cell', '血常规', '×10¹²/L'),
('血红蛋白', 'HGB', 'Hemoglobin', '血常规', 'g/L'),
('红细胞压积', 'HCT', 'Hematocrit', '血常规', '%'),
('平均红细胞体积', 'MCV', 'Mean Corpuscular Volume', '血常规', 'fL'),
('平均红细胞血红蛋白含量', 'MCH', 'Mean Corpuscular Hemoglobin', '血常规', 'pg'),
('平均红细胞血红蛋白浓度', 'MCHC', 'Mean Corpuscular Hemoglobin Concentration', '血常规', 'g/L'),
('血小板计数', 'PLT', 'Platelet', '血常规', '×10⁹/L'),
('谷丙转氨酶', 'ALT', 'Alanine Aminotransferase', '肝功能', 'U/L'),
('谷草转氨酶', 'AST', 'Aspartate Aminotransferase', '肝功能', 'U/L'),
('总胆红素', 'TBIL', 'Total Bilirubin', '肝功能', 'μmol/L'),
('直接胆红素', 'DBIL', 'Direct Bilirubin', '肝功能', 'μmol/L'),
('总蛋白', 'TP', 'Total Protein', '肝功能', 'g/L'),
('白蛋白', 'ALB', 'Albumin', '肝功能', 'g/L'),
('肌酐', 'Cr', 'Creatinine', '肾功能', 'μmol/L'),
('尿素氮', 'BUN', 'Blood Urea Nitrogen', '肾功能', 'mmol/L'),
('尿酸', 'UA', 'Uric Acid', '肾功能', 'μmol/L'),
('空腹血糖', 'FBG', 'Fasting Blood Glucose', '血糖', 'mmol/L'),
('甘油三酯', 'TG', 'Triglyceride', '血脂', 'mmol/L'),
('总胆固醇', 'TC', 'Total Cholesterol', '血脂', 'mmol/L'),
('高密度脂蛋白胆固醇', 'HDL-C', 'High-Density Lipoprotein Cholesterol', '血脂', 'mmol/L'),
('低密度脂蛋白胆固醇', 'LDL-C', 'Low-Density Lipoprotein Cholesterol', '血脂', 'mmol/L');

-- 初始化指标别名
INSERT INTO Alias (item_id, alias_name) VALUES
(1, '白细胞'), (1, 'WBC'),
(2, '红细胞'), (2, 'RBC'),
(3, '血色素'), (3, 'HGB'),
(9, '丙氨酸氨基转移酶'), (9, 'GPT'),
(10, '天门冬氨酸氨基转移酶'), (10, 'GOT');
