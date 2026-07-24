from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from db.session import get_db
from db.models import LabResult, LabItem, Report, Hospital
from core.security import get_current_user
from core.schemas import ResponseModel, TrendDataPoint, TrendAnalysisResponse

router = APIRouter(prefix="/api/v1/trend", tags=["趋势分析"])


@router.get("/items", response_model=ResponseModel)
async def get_trend_items(
    keyword: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(LabItem)
    
    if keyword:
        query = query.filter(
            (LabItem.item_name.like(f"%{keyword}%")) |
            (LabItem.abbr.like(f"%{keyword}%"))
        )
    
    items = query.order_by(LabItem.category, LabItem.item_name).all()
    return ResponseModel(data=[{
        "item_id": item.item_id,
        "item_name": item.item_name,
        "abbr": item.abbr,
        "category": item.category,
        "standard_unit": item.standard_unit
    } for item in items])


@router.get("/analysis", response_model=ResponseModel)
async def get_trend_analysis(
    item_ids: List[int] = Query(..., description="检验项目ID列表，支持多个指标"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    results = []
    
    for item_id in item_ids:
        item = db.query(LabItem).filter(LabItem.item_id == item_id).first()
        if not item:
            continue
        
        query = db.query(LabResult, Report).filter(
            LabResult.item_id == item_id,
            LabResult.report_id == Report.report_id
        )
        
        if start_date:
            query = query.filter(Report.sample_time >= start_date)
        if end_date:
            query = query.filter(Report.sample_time <= end_date)
        
        query_results = query.order_by(Report.sample_time).all()
        
        data_points = []
        prev_value = None
        seen_dates = set()
        
        for result, report in query_results:
            if report.sample_time is None:
                continue
                
            date_key = report.sample_time.date()
            if date_key in seen_dates:
                continue
            seen_dates.add(date_key)
            
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
            
            data_points.append(TrendDataPoint(
                time=report.sample_time,
                value=current_value,
                hospital=hospital.hospital_name if hospital else None,
                flag=result.flag,
                trend=trend,
                report_id=report.report_id if report.is_delete == 0 else None
            ))
            
            prev_value = current_value
        
        results.append({
            "item_id": item.item_id,
            "item_name": item.item_name,
            "abbr": item.abbr,
            "unit": item.standard_unit,
            "data": data_points
        })
    
    return ResponseModel(data=results)
