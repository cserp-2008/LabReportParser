"""人工复核与审计日志 API

依据设计说明书 2.1.7 人工复核与审计需求：
- 指标全字段编辑
- 复核状态枚举：未复核、已复核、人工修改
- 审计日志完整记录
- 支持单条指标回滚至原始 OCR 识别数据
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import json
import logging
from db.session import get_db
from db.models import LabResult, Report, AuditLog
from core.security import get_current_user
from core.schemas import ResponseModel, ReviewUpdateRequest, AuditLogItem
from parser.template_learner import TemplateLearner

router = APIRouter(prefix="/api/v1/review", tags=["人工复核"])
logger = logging.getLogger(__name__)


@router.put("/{result_id}", response_model=ResponseModel)
async def update_lab_result(
    result_id: int,
    update: ReviewUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改单条检验指标（人工复核），result_id=0时为新增"""
    if result_id == 0:
        if not hasattr(update, 'report_id') or not update.report_id:
            raise HTTPException(status_code=400, detail="新增指标需要指定report_id")
        
        report = db.query(Report).filter(Report.report_id == update.report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")
        
        new_value = {
            "raw_item_name": update.raw_item_name,
            "raw_value": update.raw_value,
            "unit": update.unit,
            "reference_text": update.reference_text,
            "flag": update.flag,
        }
        
        result = LabResult(
            report_id=update.report_id,
            page_id=0,
            source_file="manual",
            source_path="manual",
            raw_item_name=update.raw_item_name,
            raw_value=update.raw_value,
            unit=update.unit,
            reference_low=None,
            reference_high=None,
            reference_text=update.reference_text,
            flag=update.flag,
            review_status=2,
        )
        db.add(result)
        
        audit = AuditLog(
            operate_user_id=current_user.user_id,
            operate_type="CREATE_RESULT",
            target_table="LabResult",
            target_id="new",
            old_value="",
            new_value=json.dumps(new_value, ensure_ascii=False),
        )
        db.add(audit)
        
        report.review_status = 2
        db.commit()
        db.refresh(result)

        # 自动学习报告特征
        learner = TemplateLearner(db)
        learner.learn_from_review(result)

        return ResponseModel(data={"result_id": result.result_id, "message": "新增成功"})
    
    result = db.query(LabResult).filter(LabResult.result_id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="检验结果不存在")

    # 记录原始值用于审计
    old_value = {
        "raw_item_name": result.raw_item_name,
        "raw_value": result.raw_value,
        "unit": result.unit,
        "reference_low": float(result.reference_low) if result.reference_low else None,
        "reference_high": float(result.reference_high) if result.reference_high else None,
        "reference_text": result.reference_text,
        "flag": result.flag,
    }

    # 应用修改
    update_data = update.model_dump(exclude_unset=True)
    logger.info(f"update_lab_result: result_id={result_id}, update_data={update_data}")
    new_value = dict(old_value)
    for field, value in update_data.items():
        setattr(result, field, value)
        new_value[field] = value

    # 标记为人工修改
    result.review_status = 2

    # 同步更新报告复核状态
    report = db.query(Report).filter(Report.report_id == result.report_id).first()
    if report:
        report.review_status = 2

    # 写入审计日志
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="UPDATE_RESULT",
        target_table="LabResult",
        target_id=str(result_id),
        old_value=json.dumps(old_value, ensure_ascii=False),
        new_value=json.dumps(new_value, ensure_ascii=False),
    )
    db.add(audit)
    db.commit()

    # 自动学习报告特征
    learner = TemplateLearner(db)
    learner.learn_from_review(result, old_values=old_value)

    return ResponseModel(data={"result_id": result_id, "message": "修改成功"})


@router.delete("/{result_id}", response_model=ResponseModel)
async def delete_lab_result(
    result_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除单条检验指标"""
    result = db.query(LabResult).filter(LabResult.result_id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="检验结果不存在")

    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="DELETE_RESULT",
        target_table="LabResult",
        target_id=str(result_id),
        old_value=json.dumps({
            "raw_item_name": result.raw_item_name,
            "raw_value": result.raw_value,
        }, ensure_ascii=False),
        new_value="",
    )
    db.add(audit)
    
    db.delete(result)
    db.commit()

    return ResponseModel(data={"result_id": result_id, "message": "删除成功"})


@router.post("/{result_id}/rollback", response_model=ResponseModel)
async def rollback_lab_result(
    result_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """回滚单条指标至原始 OCR 识别数据（即最近一次修改前的值）"""
    result = db.query(LabResult).filter(LabResult.result_id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="检验结果不存在")

    # 查找最近一次修改该结果的审计日志
    audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.target_table == "LabResult",
            AuditLog.target_id == str(result_id),
            AuditLog.operate_type == "UPDATE_RESULT",
        )
        .order_by(AuditLog.operate_time.desc())
        .first()
    )

    if not audit:
        raise HTTPException(status_code=404, detail="无历史修改记录，无法回滚")

    old_data = json.loads(audit.old_value)

    # 记录当前值
    current_value = {
        "raw_item_name": result.raw_item_name,
        "raw_value": result.raw_value,
        "unit": result.unit,
        "reference_low": float(result.reference_low) if result.reference_low else None,
        "reference_high": float(result.reference_high) if result.reference_high else None,
        "reference_text": result.reference_text,
        "flag": result.flag,
    }

    # 恢复旧值
    for field, value in old_data.items():
        if value is not None:
            setattr(result, field, value)
    result.review_status = 2

    # 写入回滚审计日志
    rollback_audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="ROLLBACK_RESULT",
        target_table="LabResult",
        target_id=str(result_id),
        old_value=json.dumps(current_value, ensure_ascii=False),
        new_value=json.dumps(old_data, ensure_ascii=False),
    )
    db.add(rollback_audit)
    db.commit()

    return ResponseModel(data={"result_id": result_id, "message": "已回滚至原始值"})


@router.put("/report/{report_id}/status", response_model=ResponseModel)
async def update_report_review_status(
    report_id: str,
    status: int = 1,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新报告复核状态（0未复核 1已复核 2人工修改）"""
    report = db.query(Report).filter(Report.report_id == report_id, Report.is_delete == 0).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    old_status = report.review_status
    report.review_status = status

    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="UPDATE_REVIEW_STATUS",
        target_table="Report",
        target_id=report_id,
        old_value=json.dumps({"review_status": old_status}),
        new_value=json.dumps({"review_status": status}),
    )
    db.add(audit)
    db.commit()

    return ResponseModel(data={"report_id": report_id, "review_status": status})


@router.get("/audit-logs", response_model=ResponseModel)
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    target_table: Optional[str] = None,
    target_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询审计日志"""
    query = db.query(AuditLog)
    if target_table:
        query = query.filter(AuditLog.target_table == target_table)
    if target_id:
        query = query.filter(AuditLog.target_id == target_id)

    total = query.count()
    logs = query.order_by(AuditLog.operate_time.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return ResponseModel(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": [AuditLogItem.from_orm(log) for log in logs],
    })
