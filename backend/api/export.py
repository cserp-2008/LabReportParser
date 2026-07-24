"""数据导出 API

依据设计说明书 2.1.9 数据导出需求：
支持 Excel、CSV 批量导出；导出字段包含医院、报告时间、患者信息、
标准指标、结果、单位、参考范围、异常标记、源文件、页码、置信度、复核状态。
"""
import csv
import io
import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from db.session import get_db
from db.models import LabResult, Report, LabItem, Hospital, ReportPage
from core.security import get_current_user

router = APIRouter(prefix="/api/v1/export", tags=["数据导出"])
logger = logging.getLogger(__name__)

EXPORT_HEADERS = [
    "报告ID", "医院", "患者姓名", "性别", "年龄", "采样时间", "报告时间",
    "原始项目名", "标准项目名", "缩写", "结果", "单位",
    "参考下限", "参考上限", "参考文本", "异常标记",
    "源文件", "页码", "置信度", "复核状态",
]

REVIEW_STATUS_MAP = {0: "未复核", 1: "已复核", 2: "人工修改"}


@router.get("/csv")
async def export_csv(
    report_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出检验结果为 CSV"""
    query = db.query(LabResult, Report, LabItem, Hospital).outerjoin(
        Report, LabResult.report_id == Report.report_id
    ).outerjoin(
        LabItem, LabResult.item_id == LabItem.item_id
    ).outerjoin(
        Hospital, Report.hospital_id == Hospital.hospital_id
    ).filter(Report.is_delete == 0)

    if report_id:
        query = query.filter(LabResult.report_id == report_id)

    rows = query.all()

    output = io.StringIO()
    # 写入 UTF-8 BOM 以兼容 Excel
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(EXPORT_HEADERS)

    for result, report, item, hospital in rows:
        writer.writerow([
            report.report_id,
            hospital.hospital_name if hospital else "",
            report.patient_name or "",
            report.gender or "",
            report.age or "",
            report.sample_time.strftime("%Y-%m-%d %H:%M") if report.sample_time else "",
            report.report_time.strftime("%Y-%m-%d %H:%M") if report.report_time else "",
            result.raw_item_name,
            item.item_name if item else "",
            item.abbr if item else "",
            result.raw_value or "",
            result.unit or "",
            float(result.reference_low) if result.reference_low else "",
            float(result.reference_high) if result.reference_high else "",
            result.reference_text or "",
            result.flag or "",
            result.source_file,
            result.page_id,
            float(result.ocr_confidence) if result.ocr_confidence else "",
            REVIEW_STATUS_MAP.get(result.review_status, "未复核"),
        ])

    content = output.getvalue()
    output.close()

    filename = f"lab_results_{report_id or 'all'}.csv"
    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/excel")
async def export_excel(
    report_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出检验结果为 Excel (xlsx)"""
    try:
        from openpyxl import Workbook
    except ImportError:
        return {"code": 500, "msg": "openpyxl 未安装，无法导出 Excel"}

    query = db.query(LabResult, Report, LabItem, Hospital).outerjoin(
        Report, LabResult.report_id == Report.report_id
    ).outerjoin(
        LabItem, LabResult.item_id == LabItem.item_id
    ).outerjoin(
        Hospital, Report.hospital_id == Hospital.hospital_id
    ).filter(Report.is_delete == 0)

    if report_id:
        query = query.filter(LabResult.report_id == report_id)

    rows = query.all()

    wb = Workbook()
    ws = wb.active
    ws.title = "检验结果"
    ws.append(EXPORT_HEADERS)

    for result, report, item, hospital in rows:
        ws.append([
            report.report_id,
            hospital.hospital_name if hospital else "",
            report.patient_name or "",
            report.gender or "",
            report.age or "",
            report.sample_time.strftime("%Y-%m-%d %H:%M") if report.sample_time else None,
            report.report_time.strftime("%Y-%m-%d %H:%M") if report.report_time else None,
            result.raw_item_name,
            item.item_name if item else "",
            item.abbr if item else "",
            result.raw_value or "",
            result.unit or "",
            float(result.reference_low) if result.reference_low else None,
            float(result.reference_high) if result.reference_high else None,
            result.reference_text or "",
            result.flag or "",
            result.source_file,
            result.page_id,
            float(result.ocr_confidence) if result.ocr_confidence else None,
            REVIEW_STATUS_MAP.get(result.review_status, "未复核"),
        ])

    # 设置列宽
    for col_idx in range(1, len(EXPORT_HEADERS) + 1):
        ws.column_dimensions[chr(64 + col_idx) if col_idx <= 26 else "Z"].width = 15

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"lab_results_{report_id or 'all'}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
