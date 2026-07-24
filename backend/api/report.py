from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import json
from db.session import get_db
from db.models import Report, LabResult, LabItem, ReportPage, Hospital, AuditLog
from core.security import get_current_user
from core.schemas import ResponseModel, ReportListItem, ReportDetail, LabResultItem

router = APIRouter(prefix="/api/v1/report", tags=["报告管理"])


@router.get("/parser/list", response_model=ResponseModel)
async def get_parser_list():
    """获取可用的解析引擎列表"""
    parsers = []
    
    parsers.append({"code": "common", "name": "通用解析器", "description": "适用于未识别医院的通用解析"})
    
    try:
        from parser.nbmc_parser import NBMCParser
        parsers.append({"code": "nbmc", "name": "南京明基医院", "description": "南京明基医院专用解析器"})
    except ImportError:
        pass
    
    try:
        from parser.jph_parser import JPHParser
        parsers.append({"code": "jph", "name": "江苏省人民医院", "description": "江苏省人民医院专用解析器"})
    except ImportError:
        pass
    
    try:
        from parser.nsh_parser import NSHParser
        parsers.append({"code": "nsh", "name": "南京市第二医院", "description": "南京市第二医院专用解析器"})
    except ImportError:
        pass
    
    return ResponseModel(data=parsers)


@router.get("/list", response_model=ResponseModel)
async def get_report_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    pageSize: Optional[int] = None,
    keyword: Optional[str] = None,
    hospital_id: Optional[int] = None,
    review_status: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    file_type: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if pageSize is not None:
        page_size = pageSize
    
    query = db.query(Report).filter(Report.is_delete == 0)
    
    if keyword:
        query = query.filter(
            (Report.file_name.like(f"%{keyword}%")) |
            (Report.patient_name.like(f"%{keyword}%"))
        )
    
    if hospital_id:
        query = query.filter(Report.hospital_id == hospital_id)
    
    if review_status is not None:
        query = query.filter(Report.review_status == review_status)
    
    if start_date:
        query = query.filter(Report.create_time >= start_date)
    
    if end_date:
        query = query.filter(Report.create_time <= end_date)
    
    if file_type:
        query = query.filter(Report.file_type == file_type)
    
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
            create_time=report.create_time,
            hospital_name=hospital.hospital_name if hospital else None
        ))
    
    return ResponseModel(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": report_list
    })


@router.get("/{report_id}/neighbors", response_model=ResponseModel)
async def get_report_neighbors(
    report_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前报告的上一个和下一个报告（按创建时间排序）"""
    current_report = db.query(Report).filter(Report.report_id == report_id, Report.is_delete == 0).first()
    if not current_report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    prev_report = db.query(Report).filter(
        Report.is_delete == 0,
        Report.create_time < current_report.create_time
    ).order_by(Report.create_time.desc()).first()
    
    next_report = db.query(Report).filter(
        Report.is_delete == 0,
        Report.create_time > current_report.create_time
    ).order_by(Report.create_time.asc()).first()
    
    result = {
        "prev_report_id": prev_report.report_id if prev_report else None,
        "prev_file_name": prev_report.file_name if prev_report else None,
        "next_report_id": next_report.report_id if next_report else None,
        "next_file_name": next_report.file_name if next_report else None,
    }
    
    return ResponseModel(data=result)


@router.get("/{report_id}", response_model=ResponseModel)
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
        result_items.append(LabResultItem(
            result_id=result.result_id,
            raw_item_name=result.raw_item_name,
            item_name=item.item_name if item else None,
            abbr=item.abbr if item else None,
            raw_value=result.raw_value,
            value_numeric=float(result.value_numeric) if result.value_numeric else None,
            unit=result.unit,
            reference_low=float(result.reference_low) if result.reference_low else None,
            reference_high=float(result.reference_high) if result.reference_high else None,
            reference_text=result.reference_text,
            flag=result.flag,
            review_status=result.review_status,
            page_no=result.page_id,
            bbox_left=result.bbox_left,
            bbox_top=result.bbox_top,
            bbox_right=result.bbox_right,
            bbox_bottom=result.bbox_bottom
        ))
    
    page_list = []
    for page in pages:
        page_list.append({
            "page_no": page.page_no,
            "preview_url": f"/api/v1/preview/{report_id}/{page.page_no}",
            "width": page.width,
            "height": page.height
        })
    
    detail = ReportDetail(
        report_id=report.report_id,
        patient_name=report.patient_name,
        gender=report.gender,
        age=report.age,
        sample_time=report.sample_time,
        report_time=report.report_time,
        hospital_name=hospital.hospital_name if hospital else None,
        file_name=report.file_name,
        quality_score=report.quality_score,
        review_status=report.review_status,
        page_count=report.page_count,
        results=result_items,
        pages=page_list
    )

    return ResponseModel(data=detail)


class BatchUpdateRequest(BaseModel):
    report_ids: List[str]
    review_status: int


@router.post("/batch/review", response_model=ResponseModel)
async def batch_update_review_status(
    request: BatchUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量更新报告复核状态"""
    count = 0
    for report_id in request.report_ids:
        report = db.query(Report).filter(Report.report_id == report_id, Report.is_delete == 0).first()
        if report:
            old_status = report.review_status
            report.review_status = request.review_status
            count += 1
            
            audit = AuditLog(
                operate_user_id=current_user.user_id,
                operate_type="BATCH_UPDATE_REVIEW",
                target_table="Report",
                target_id=report_id,
                old_value=json.dumps({"review_status": old_status}, ensure_ascii=False),
                new_value=json.dumps({"review_status": request.review_status}, ensure_ascii=False),
            )
            db.add(audit)
    
    db.commit()
    
    return ResponseModel(data={"updated_count": count})


class BatchDeleteRequest(BaseModel):
    report_ids: List[str]


@router.post("/batch/delete", response_model=ResponseModel)
async def batch_delete_reports(
    request: BatchDeleteRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量删除报告（软删除）"""
    count = 0
    for report_id in request.report_ids:
        report = db.query(Report).filter(Report.report_id == report_id, Report.is_delete == 0).first()
        if report:
            report.is_delete = 1
            count += 1

            audit = AuditLog(
                operate_user_id=current_user.user_id,
                operate_type="BATCH_DELETE_REPORT",
                target_table="Report",
                target_id=report_id,
                old_value=json.dumps({"file_name": report.file_name}, ensure_ascii=False),
                new_value=json.dumps({"is_delete": 1}, ensure_ascii=False),
            )
            db.add(audit)

    db.commit()

    return ResponseModel(data={"deleted_count": count})


@router.get("/export", response_model=ResponseModel)
async def export_reports(
    report_ids: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出报告数据"""
    if report_ids:
        report_id_list = report_ids.split(",")
        reports = db.query(Report).filter(Report.report_id.in_(report_id_list), Report.is_delete == 0).all()
    else:
        reports = db.query(Report).filter(Report.is_delete == 0).all()
    
    export_data = []
    for report in reports:
        hospital = db.query(Hospital).filter(Hospital.hospital_id == report.hospital_id).first()
        results = db.query(LabResult).filter(LabResult.report_id == report.report_id).all()
        
        for result in results:
            item = db.query(LabItem).filter(LabItem.item_id == result.item_id).first()
            export_data.append({
                "report_id": report.report_id,
                "file_name": report.file_name,
                "patient_name": report.patient_name,
                "gender": report.gender,
                "age": report.age,
                "sample_time": str(report.sample_time),
                "hospital_name": hospital.hospital_name if hospital else "",
                "item_name": item.item_name if item else result.raw_item_name,
                "raw_item_name": result.raw_item_name,
                "raw_value": result.raw_value,
                "value_numeric": float(result.value_numeric) if result.value_numeric else None,
                "unit": result.unit,
                "reference_low": float(result.reference_low) if result.reference_low else None,
                "reference_high": float(result.reference_high) if result.reference_high else None,
                "reference_text": result.reference_text,
                "flag": result.flag,
                "review_status": result.review_status,
                "create_time": str(report.create_time)
            })
    
    return ResponseModel(data=export_data)


@router.get("/stats", response_model=ResponseModel)
async def get_report_stats(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取报告统计数据"""
    total = db.query(Report).filter(Report.is_delete == 0).count()
    pending = db.query(Report).filter(Report.is_delete == 0, Report.review_status == 0).count()
    
    from datetime import datetime
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly = db.query(Report).filter(Report.is_delete == 0, Report.create_time >= month_start).count()
    
    abnormal = db.query(LabResult).filter(LabResult.flag.isnot(None)).count()
    
    return ResponseModel(data={
        "total": total,
        "pending": pending,
        "monthly": monthly,
        "abnormal": abnormal
    })


@router.post("/{report_id}/reparse", response_model=ResponseModel)
async def reparse_report(
    report_id: str,
    parser_code: Optional[str] = None,
    hospital_id: Optional[int] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重新解析报告（删除旧结果并重新识别）
    
    参数:
    - parser_code: 可选，手动指定解析引擎（common/jph/nbmc/nsh），不指定则自动识别医院
    - hospital_id: 可选，手动指定医院ID，会先更新报告的医院信息再解析
    """
    report = db.query(Report).filter(Report.report_id == report_id, Report.is_delete == 0).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    old_count = db.query(LabResult).filter(LabResult.report_id == report_id).count()
    db.query(LabResult).filter(LabResult.report_id == report_id).delete()
    
    if hospital_id is not None:
        hospital = db.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()
        if hospital:
            report.hospital_id = hospital_id
            db.flush()
            if parser_code is None and hospital.parser_code:
                parser_code = hospital.parser_code.lower()
    
    from parser.service import ParseService
    service = ParseService(db)
    result = service.parse_report(report, parser_code=parser_code)
    
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="REPARSE_REPORT",
        target_table="Report",
        target_id=report_id,
        old_value=json.dumps({"result_count": old_count}, ensure_ascii=False),
        new_value=json.dumps({"result_count": result.get("result_count", 0)}, ensure_ascii=False),
    )
    db.add(audit)
    db.commit()
    
    return ResponseModel(data={
        "report_id": report_id,
        "result_count": result.get("result_count", 0),
        "message": "重新解析完成"
    })


@router.delete("/{report_id}", response_model=ResponseModel)
async def delete_report(
    report_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除报告（软删除）"""
    report = db.query(Report).filter(Report.report_id == report_id, Report.is_delete == 0).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    report.is_delete = 1

    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="DELETE_REPORT",
        target_table="Report",
        target_id=report_id,
        old_value=json.dumps({"file_name": report.file_name}, ensure_ascii=False),
        new_value=json.dumps({"is_delete": 1}, ensure_ascii=False),
    )
    db.add(audit)
    db.commit()

    return ResponseModel(data={"report_id": report_id, "message": "删除成功"})
