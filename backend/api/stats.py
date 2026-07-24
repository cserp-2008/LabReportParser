"""仪表盘统计 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime
from db.session import get_db
from db.models import Report, LabResult
from core.security import get_current_user
from core.schemas import ResponseModel, DashboardStats

router = APIRouter(prefix="/api/v1/stats", tags=["统计"])


@router.get("/dashboard", response_model=ResponseModel)
async def get_dashboard_stats(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取首页仪表盘统计数据"""
    now = datetime.now()
    current_month = now.month
    current_year = now.year

    total = db.query(Report).filter(Report.is_delete == 0).count()
    pending = db.query(Report).filter(
        Report.is_delete == 0, Report.review_status == 0
    ).count()
    monthly = db.query(Report).filter(
        Report.is_delete == 0,
        extract("year", Report.create_time) == current_year,
        extract("month", Report.create_time) == current_month,
    ).count()
    abnormal = db.query(LabResult).filter(
        LabResult.flag.in_(["↑", "↓"])
    ).distinct(LabResult.report_id).count()

    stats = DashboardStats(
        total=total,
        pending=pending,
        monthly=monthly,
        abnormal=abnormal,
    )
    return ResponseModel(data=stats)
