from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import shutil
import hashlib
import uuid

# 导入我们的简单模型
from db.models_simple import (
    Base, User, Role, UserRole, LabItem, Alias, Report, LabResult, ReportPage,
    UploadTask, Hospital
)

# 配置
SECRET_KEY = "labreportparser-secret-key-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
STORAGE_ROOT = "../storage"

# 创建数据库连接
DATABASE_URL = "sqlite:///./labreport.db"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建所有表
Base.metadata.create_all(bind=engine)

# 安全工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_enable:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


# Pydantic 模型
class ResponseModel(BaseModel):
    code: int = 0
    msg: str = "success"
    data: Optional[Any] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    user_id: int
    username: str
    real_name: Optional[str]


class ReportListItem(BaseModel):
    report_id: str
    file_name: str
    file_type: str
    patient_name: Optional[str]
    sample_time: Optional[datetime]
    quality_score: Optional[float]
    review_status: int
    create_time: datetime


# 创建 FastAPI 应用
app = FastAPI(title="LabReportParser API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 认证接口
@app.post("/api/v1/auth/login", response_model=ResponseModel)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    if not user.is_enable:
        raise HTTPException(status_code=400, detail="用户已禁用")
    
    access_token = create_access_token(data={"sub": user.username})
    return ResponseModel(data={"access_token": access_token, "token_type": "bearer"})


@app.get("/api/v1/auth/me", response_model=ResponseModel)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    user_info = UserInfo(
        user_id=current_user.user_id,
        username=current_user.username,
        real_name=current_user.real_name
    )
    return ResponseModel(data=user_info)


# 报告列表接口
@app.get("/api/v1/report/list", response_model=ResponseModel)
async def get_report_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Report).filter(Report.is_delete == 0)
    
    if keyword:
        query = query.filter(
            (Report.file_name.like(f"%{keyword}%")) |
            (Report.patient_name.like(f"%{keyword}%"))
        )
    
    total = query.count()
    reports = query.order_by(Report.create_time.desc()).offset((page-1)*page_size).limit(page_size).all()
    
    report_list = []
    for report in reports:
        hospital = db.query(Hospital).filter(Hospital.hospital_id == report.hospital_id).first()
        report_list.append(ReportListItem(
            report_id=report.report_id,
            file_name=report.file_name,
            file_type=report.file_type,
            patient_name=report.patient_name,
            sample_time=report.sample_time,
            quality_score=report.quality_score,
            review_status=report.review_status,
            create_time=report.create_time
        ))
    
    return ResponseModel(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": report_list
    })


# 报告详情接口
@app.get("/api/v1/report/{report_id}", response_model=ResponseModel)
async def get_report_detail(
    report_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(Report).filter(Report.report_id == report_id, Report.is_delete == 0).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    hospital = db.query(Hospital).filter(Hospital.hospital_id == report.hospital_id).first()
    pages = db.query(ReportPage).filter(ReportPage.report_id == report_id).order_by(ReportPage.page_no).all()
    results = db.query(LabResult).filter(LabResult.report_id == report_id).all()
    
    result_items = []
    for result in results:
        item = db.query(LabItem).filter(LabItem.item_id == result.item_id).first()
        result_items.append({
            "result_id": result.result_id,
            "raw_item_name": result.raw_item_name,
            "item_name": item.item_name if item else None,
            "abbr": item.abbr if item else None,
            "raw_value": result.raw_value,
            "value_numeric": float(result.value_numeric) if result.value_numeric else None,
            "unit": result.unit,
            "reference_low": float(result.reference_low) if result.reference_low else None,
            "reference_high": float(result.reference_high) if result.reference_high else None,
            "reference_text": result.reference_text,
            "flag": result.flag,
            "review_status": result.review_status,
            "page_no": result.page_id,
            "bbox_left": result.bbox_left,
            "bbox_top": result.bbox_top,
            "bbox_right": result.bbox_right,
            "bbox_bottom": result.bbox_bottom
        })
    
    page_list = []
    for page in pages:
        page_list.append({
            "page_no": page.page_no,
            "preview_url": f"/api/v1/preview/{report_id}/{page.page_no}",
            "width": page.width,
            "height": page.height
        })
    
    return ResponseModel(data={
        "report_id": report.report_id,
        "patient_name": report.patient_name,
        "gender": report.gender,
        "age": report.age,
        "sample_time": report.sample_time,
        "report_time": report.report_time,
        "hospital_name": hospital.hospital_name if hospital else None,
        "file_name": report.file_name,
        "quality_score": report.quality_score,
        "review_status": report.review_status,
        "page_count": report.page_count,
        "results": result_items,
        "pages": page_list
    })


# 文件上传接口
def generate_report_id() -> str:
    return str(uuid.uuid4()).replace('-', '')


def generate_task_id() -> str:
    return str(uuid.uuid4()).replace('-', '')


def calculate_md5(file_path: str) -> str:
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_storage_path(report_id: str, filename: str) -> str:
    date_str = datetime.now().strftime("%Y/%m")
    dir_path = os.path.join(STORAGE_ROOT, "report", date_str)
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, f"{report_id}_{filename}")


@app.post("/api/v1/upload/file", response_model=ResponseModel)
async def upload_file(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task_id = generate_task_id()
    
    task = UploadTask(
        task_id=task_id,
        user_id=current_user.user_id,
        file_total=1,
        status=2,
        progress=100,
        success_count=1,
        message="上传成功"
    )
    db.add(task)
    db.commit()
    
    report_id = generate_report_id()
    storage_path = get_storage_path(report_id, file.filename)
    
    with open(storage_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_md5 = calculate_md5(storage_path)
    file_size = os.path.getsize(storage_path)
    
    report = Report(
        report_id=report_id,
        task_id=task_id,
        file_name=file.filename,
        file_type=file.filename.split('.')[-1].lower(),
        file_size=file_size,
        file_md5=file_md5,
        storage_path=storage_path,
        page_count=1,
        quality_score=0,
        review_status=0
    )
    db.add(report)
    
    page = ReportPage(
        report_id=report_id,
        page_no=1,
        width=800,
        height=600
    )
    db.add(page)
    db.commit()
    
    return ResponseModel(data={
        "task_id": task_id,
        "report_id": report_id
    })


# 趋势分析接口
@app.get("/api/v1/trend/items", response_model=ResponseModel)
async def get_trend_items(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    items = db.query(LabItem).order_by(LabItem.category, LabItem.item_name).all()
    return ResponseModel(data=[{
        "item_id": item.item_id,
        "item_name": item.item_name,
        "abbr": item.abbr,
        "category": item.category,
        "standard_unit": item.standard_unit
    } for item in items])


@app.get("/api/v1/trend/analysis/{item_id}", response_model=ResponseModel)
async def get_trend_analysis(
    item_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(LabItem).filter(LabItem.item_id == item_id).first()
    if not item:
        return ResponseModel(code=404, msg="检验项目不存在")
    
    query = db.query(LabResult, Report).filter(
        LabResult.item_id == item_id,
        LabResult.report_id == Report.report_id,
        Report.is_delete == 0
    )
    
    if start_date:
        query = query.filter(Report.sample_time >= start_date)
    if end_date:
        query = query.filter(Report.sample_time <= end_date)
    
    results = query.order_by(Report.sample_time).all()
    
    data_points = []
    prev_value = None
    for result, report in results:
        hospital = db.query(Hospital).filter(Hospital.hospital_id == report.hospital_id).first()
        
        trend = None
        current_value = float(result.value_numeric) if result.value_numeric else None
        
        if current_value is not None and prev_value is not None:
            if current_value > prev_value:
                trend = "上升"
            elif current_value < prev_value:
                trend = "下降"
            else:
                trend = "平稳"
        
        data_points.append({
            "time": report.sample_time,
            "value": current_value,
            "hospital": hospital.hospital_name if hospital else None,
            "flag": result.flag,
            "trend": trend
        })
        prev_value = current_value
    
    return ResponseModel(data={
        "item_id": item.item_id,
        "item_name": item.item_name,
        "abbr": item.abbr,
        "unit": item.standard_unit,
        "data": data_points
    })


# 根路径
@app.get("/")
async def root():
    return {"message": "LabReportParser API Server", "version": "3.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
