"""异步任务管理 API

依据设计说明书 2.1.11 系统配置与异步任务：
任务监控：查看队列、终止任务、失败文件一键重解析。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging
from db.session import get_db
from db.models import UploadTask, Report, User
from core.security import get_current_user
from core.schemas import ResponseModel, TaskListItem
from parser.service import ParseService

router = APIRouter(prefix="/api/v1/task", tags=["任务管理"])
logger = logging.getLogger(__name__)


@router.get("/list", response_model=ResponseModel)
async def get_task_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[int] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询上传任务列表"""
    query = db.query(UploadTask)
    if status is not None:
        query = query.filter(UploadTask.status == status)

    total = query.count()
    tasks = query.order_by(UploadTask.start_time.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return ResponseModel(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": [TaskListItem.from_orm(t) for t in tasks],
    })


@router.get("/{task_id}", response_model=ResponseModel)
async def get_task_detail(
    task_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询单个任务详情"""
    task = db.query(UploadTask).filter(UploadTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    reports = db.query(Report).filter(Report.task_id == task_id).all()
    report_list = [{
        "report_id": r.report_id,
        "file_name": r.file_name,
        "quality_score": r.quality_score,
        "review_status": r.review_status,
    } for r in reports]

    data = TaskListItem.from_orm(task).dict()
    data["reports"] = report_list
    return ResponseModel(data=data)


@router.post("/reparse/{report_id}", response_model=ResponseModel)
async def reparse_report(
    report_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重新解析报告（失败重试）"""
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    service = ParseService(db)
    result = service.parse_report(report)

    return ResponseModel(data=result)
