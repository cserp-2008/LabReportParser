from pydantic import BaseModel
from typing import Optional, Any, List, Dict
from datetime import datetime


class ResponseModel(BaseModel):
    code: int = 0
    msg: str = "success"
    data: Optional[Any] = None


class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    user_id: int
    username: str
    real_name: Optional[str]

    class Config:
        from_attributes = True


class ReportListItem(BaseModel):
    report_id: str
    file_name: str
    file_type: str
    patient_name: Optional[str]
    sample_time: Optional[datetime]
    quality_score: Optional[float]
    review_status: int
    create_time: datetime
    hospital_name: Optional[str]

    class Config:
        from_attributes = True


class LabResultItem(BaseModel):
    result_id: int
    raw_item_name: str
    item_name: Optional[str]
    abbr: Optional[str]
    raw_value: Optional[str]
    value_numeric: Optional[float]
    unit: Optional[str]
    reference_low: Optional[float]
    reference_high: Optional[float]
    reference_text: Optional[str]
    flag: Optional[str]
    review_status: int
    page_no: int
    bbox_left: Optional[int]
    bbox_top: Optional[int]
    bbox_right: Optional[int]
    bbox_bottom: Optional[int]


class ReportDetail(BaseModel):
    report_id: str
    patient_name: Optional[str]
    gender: Optional[str]
    age: Optional[str]
    sample_time: Optional[datetime]
    report_time: Optional[datetime]
    hospital_name: Optional[str]
    file_name: str
    quality_score: Optional[float]
    review_status: int
    page_count: int
    results: List[LabResultItem]
    pages: List[Dict]


class PagePreviewData(BaseModel):
    page_no: int
    preview_url: str
    width: Optional[int]
    height: Optional[int]


class TrendDataPoint(BaseModel):
    time: Optional[datetime] = None
    value: Optional[float] = None
    hospital: Optional[str] = None
    flag: Optional[str] = None
    trend: Optional[str] = None
    report_id: Optional[str] = None


class TrendAnalysisResponse(BaseModel):
    item_id: int
    item_name: str
    abbr: str
    unit: Optional[str]
    data: List[TrendDataPoint]


class ReviewUpdateRequest(BaseModel):
    raw_item_name: Optional[str] = None
    raw_value: Optional[str] = None
    unit: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    reference_text: Optional[str] = None
    flag: Optional[str] = None
    report_id: Optional[str] = None


class DashboardStats(BaseModel):
    total: int = 0
    pending: int = 0
    monthly: int = 0
    abnormal: int = 0


class AuditLogItem(BaseModel):
    log_id: int
    operate_user_id: Optional[int]
    operate_type: str
    target_table: str
    target_id: str
    old_value: Optional[str]
    new_value: Optional[str]
    operate_time: datetime
    ip_address: Optional[str]

    class Config:
        from_attributes = True


class TaskListItem(BaseModel):
    task_id: str
    user_id: int
    file_total: int
    success_count: int
    fail_count: int
    status: int
    progress: float
    message: Optional[str]
    start_time: Optional[datetime]
    finish_time: Optional[datetime]

    class Config:
        from_attributes = True
