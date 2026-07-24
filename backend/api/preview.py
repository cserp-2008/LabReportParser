from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
from db.session import get_db
from db.models import Report, ReportPage
from core.security import get_current_user
from core.config import config

router = APIRouter(prefix="/api/v1/preview", tags=["预览"])


@router.get("/original/{report_id}")
async def get_original_file(
    report_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(Report).filter(Report.report_id == report_id, Report.is_delete == 0).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    if not os.path.exists(report.storage_path):
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    return FileResponse(report.storage_path, filename=report.file_name)


@router.get("/{report_id}/{page_no}")
async def get_page_preview(
    report_id: str,
    page_no: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(Report).filter(Report.report_id == report_id, Report.is_delete == 0).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    page = db.query(ReportPage).filter(ReportPage.report_id == report_id, ReportPage.page_no == page_no).first()
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")
    
    if page.preview_image_path and os.path.exists(page.preview_image_path):
        return FileResponse(page.preview_image_path)
    
    if os.path.exists(report.storage_path):
        return FileResponse(report.storage_path)
    
    raise HTTPException(status_code=404, detail="预览文件不存在")
