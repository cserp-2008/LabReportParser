from sqlalchemy import Column, Integer, String, DateTime, Text, Float, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Hospital(Base):
    __tablename__ = "Hospital"
    hospital_id = Column(Integer, primary_key=True, autoincrement=True)
    hospital_name = Column(String(200), nullable=False)
    province = Column(String(50))
    city = Column(String(50))
    parser_code = Column(String(100), nullable=False)
    create_time = Column(DateTime, default=func.now())
    update_time = Column(DateTime, default=func.now(), onupdate=func.now())


class UploadTask(Base):
    __tablename__ = "UploadTask"
    task_id = Column(String(64), primary_key=True)
    user_id = Column(Integer, nullable=False)
    file_total = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    status = Column(Integer, comment="0待处理 1处理中 2完成 3失败")
    progress = Column(Float, default=0)
    message = Column(Text)
    start_time = Column(DateTime, default=func.now())
    finish_time = Column(DateTime)


class Report(Base):
    __tablename__ = "Report"
    report_id = Column(String(64), primary_key=True)
    task_id = Column(String(64), nullable=False)
    hospital_id = Column(Integer)
    patient_name = Column(String(50))
    gender = Column(String(10))
    age = Column(String(20))
    sample_time = Column(DateTime)
    report_time = Column(DateTime)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer)
    file_md5 = Column(String(64), nullable=False)
    storage_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500))
    page_count = Column(Integer, default=1)
    quality_score = Column(Float)
    review_status = Column(Integer, default=0, comment="0未复核 1已复核 2人工修改")
    is_delete = Column(Integer, default=0)
    create_time = Column(DateTime, default=func.now())


class ReportPage(Base):
    __tablename__ = "ReportPage"
    page_id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(64), nullable=False)
    page_no = Column(Integer, nullable=False)
    preview_image_path = Column(String(500))
    width = Column(Integer)
    height = Column(Integer)
    create_time = Column(DateTime, default=func.now())


class OCRBlock(Base):
    __tablename__ = "OCRBlock"
    block_id = Column(Integer, primary_key=True, autoincrement=True)
    page_id = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    confidence = Column(Float)
    bbox_left = Column(Integer)
    bbox_top = Column(Integer)
    bbox_right = Column(Integer)
    bbox_bottom = Column(Integer)


class LabItem(Base):
    __tablename__ = "LabItem"
    item_id = Column(Integer, primary_key=True, autoincrement=True)
    item_name = Column(String(100), nullable=False)
    abbr = Column(String(50))
    english_name = Column(String(200))
    category = Column(String(50))
    standard_unit = Column(String(30))
    description = Column(Text)


class Alias(Base):
    __tablename__ = "Alias"
    alias_id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, nullable=False)
    alias_name = Column(String(100), nullable=False)


class LabResult(Base):
    __tablename__ = "LabResult"
    result_id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(64), nullable=False)
    page_id = Column(Integer, nullable=False)
    item_id = Column(Integer)
    raw_item_name = Column(String(100), nullable=False)
    raw_value = Column(String(100))
    value_numeric = Column(DECIMAL(18, 4))
    unit = Column(String(30))
    reference_low = Column(DECIMAL(18, 4))
    reference_high = Column(DECIMAL(18, 4))
    reference_text = Column(String(200))
    flag = Column(String(10), comment="↑ ↓ 正常")
    bbox_left = Column(Integer)
    bbox_top = Column(Integer)
    bbox_right = Column(Integer)
    bbox_bottom = Column(Integer)
    ocr_confidence = Column(Float)
    review_status = Column(Integer, default=0)
    source_file = Column(String(255), nullable=False)
    source_path = Column(String(500), nullable=False)


class User(Base):
    __tablename__ = "User"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    real_name = Column(String(50))
    is_enable = Column(Integer, default=1)
    create_time = Column(DateTime, default=func.now())


class Role(Base):
    __tablename__ = "Role"
    role_id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(50), unique=True, nullable=False)
    permission_list = Column(Text)


class UserRole(Base):
    __tablename__ = "UserRole"
    user_id = Column(Integer, nullable=False, primary_key=True)
    role_id = Column(Integer, nullable=False, primary_key=True)


class AuditLog(Base):
    __tablename__ = "AuditLog"
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    operate_user_id = Column(Integer)
    operate_type = Column(String(30), nullable=False)
    target_table = Column(String(50), nullable=False)
    target_id = Column(String(64), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    operate_time = Column(DateTime, default=func.now())
    ip_address = Column(String(50))
