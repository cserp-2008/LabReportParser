from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import json
from db.session import get_db
from db.models import Hospital, AuditLog
from core.security import get_current_user
from core.schemas import ResponseModel

router = APIRouter(prefix="/api/v1/hospital", tags=["医院管理"])


class HospitalCreateRequest(BaseModel):
    hospital_name: str
    province: Optional[str] = None
    city: Optional[str] = None
    parser_code: str


class HospitalUpdateRequest(BaseModel):
    hospital_name: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    parser_code: Optional[str] = None


@router.get("/list", response_model=ResponseModel)
async def get_hospital_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Hospital)
    
    if keyword:
        query = query.filter(
            (Hospital.hospital_name.like(f"%{keyword}%")) |
            (Hospital.province.like(f"%{keyword}%")) |
            (Hospital.city.like(f"%{keyword}%"))
        )
    
    total = query.count()
    hospitals = query.order_by(Hospital.create_time.desc()).offset((page-1)*page_size).limit(page_size).all()
    
    return ResponseModel(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": [{
            "hospital_id": h.hospital_id,
            "hospital_name": h.hospital_name,
            "province": h.province,
            "city": h.city,
            "parser_code": h.parser_code,
            "create_time": h.create_time
        } for h in hospitals]
    })


@router.post("/", response_model=ResponseModel)
async def create_hospital(
    request: HospitalCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if db.query(Hospital).filter(Hospital.hospital_name == request.hospital_name).first():
        raise HTTPException(status_code=400, detail="医院名称已存在")
    
    hospital = Hospital(
        hospital_name=request.hospital_name,
        province=request.province,
        city=request.city,
        parser_code=request.parser_code
    )
    db.add(hospital)
    
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="CREATE_HOSPITAL",
        target_table="Hospital",
        target_id=str(hospital.hospital_id),
        old_value="",
        new_value=json.dumps(request.dict(), ensure_ascii=False),
    )
    db.add(audit)
    
    db.commit()
    db.refresh(hospital)
    
    return ResponseModel(data={"hospital_id": hospital.hospital_id})


@router.put("/{hospital_id}", response_model=ResponseModel)
async def update_hospital(
    hospital_id: int,
    request: HospitalUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    hospital = db.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="医院不存在")
    
    old_value = json.dumps({
        "hospital_name": hospital.hospital_name,
        "province": hospital.province,
        "city": hospital.city,
        "parser_code": hospital.parser_code
    }, ensure_ascii=False)
    
    if request.hospital_name:
        hospital.hospital_name = request.hospital_name
    if request.province is not None:
        hospital.province = request.province
    if request.city is not None:
        hospital.city = request.city
    if request.parser_code:
        hospital.parser_code = request.parser_code
    
    new_value = json.dumps({
        "hospital_name": hospital.hospital_name,
        "province": hospital.province,
        "city": hospital.city,
        "parser_code": hospital.parser_code
    }, ensure_ascii=False)
    
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="UPDATE_HOSPITAL",
        target_table="Hospital",
        target_id=str(hospital_id),
        old_value=old_value,
        new_value=new_value,
    )
    db.add(audit)
    
    db.commit()
    
    return ResponseModel(data={"hospital_id": hospital_id})


@router.delete("/{hospital_id}", response_model=ResponseModel)
async def delete_hospital(
    hospital_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    hospital = db.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="医院不存在")
    
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="DELETE_HOSPITAL",
        target_table="Hospital",
        target_id=str(hospital_id),
        old_value=json.dumps({"hospital_name": hospital.hospital_name}, ensure_ascii=False),
        new_value="",
    )
    db.add(audit)
    
    db.delete(hospital)
    db.commit()
    
    return ResponseModel(data={"hospital_id": hospital_id})


@router.get("/options", response_model=ResponseModel)
async def get_hospital_options(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    hospitals = db.query(Hospital).order_by(Hospital.hospital_name).all()
    return ResponseModel(data=[{
        "value": h.hospital_id,
        "label": h.hospital_name
    } for h in hospitals])


@router.get("/{hospital_id}/template", response_model=ResponseModel)
async def get_hospital_template(
    hospital_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取医院学习到的模板特征"""
    from parser.template_learner import TemplateLearner
    learner = TemplateLearner(db)
    template = learner.get_template(hospital_id)
    if not template:
        return ResponseModel(data={"item_mappings": {}, "unit_mappings": {}, "reference_formats": {}, "learn_count": 0})
    return ResponseModel(data=template)


@router.delete("/{hospital_id}/template", response_model=ResponseModel)
async def clear_hospital_template(
    hospital_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """清除医院学习到的模板特征"""
    from parser.template_learner import TemplateLearner
    learner = TemplateLearner(db)
    success = learner.clear_template(hospital_id)
    if not success:
        raise HTTPException(status_code=404, detail="医院不存在")
    
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="CLEAR_TEMPLATE",
        target_table="Hospital",
        target_id=str(hospital_id),
        old_value="",
        new_value="",
    )
    db.add(audit)
    db.commit()
    
    return ResponseModel(data={"hospital_id": hospital_id, "message": "模板已清除"})
