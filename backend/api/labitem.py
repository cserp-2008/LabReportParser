from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import json
import csv
from io import StringIO
from db.session import get_db
from db.models import LabItem, Alias, AuditLog
from core.security import get_current_user
from core.schemas import ResponseModel

router = APIRouter(prefix="/api/v1/labitem", tags=["指标管理"])


class LabItemCreateRequest(BaseModel):
    item_name: str
    abbr: Optional[str] = None
    english_name: Optional[str] = None
    category: Optional[str] = None
    standard_unit: str
    reference_range: Optional[str] = None
    description: Optional[str] = None


class LabItemUpdateRequest(BaseModel):
    item_name: Optional[str] = None
    abbr: Optional[str] = None
    english_name: Optional[str] = None
    category: Optional[str] = None
    standard_unit: Optional[str] = None
    reference_range: Optional[str] = None
    description: Optional[str] = None


class AliasSaveRequest(BaseModel):
    aliases: List[str]


@router.get("/list", response_model=ResponseModel)
async def get_labitem_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(LabItem)
    
    if keyword:
        query = query.filter(
            (LabItem.item_name.like(f"%{keyword}%")) |
            (LabItem.abbr.like(f"%{keyword}%")) |
            (LabItem.english_name.like(f"%{keyword}%"))
        )
    
    total = query.count()
    items = query.order_by(LabItem.item_name).offset((page-1)*page_size).limit(page_size).all()
    
    result = []
    for item in items:
        alias_count = db.query(Alias).filter(Alias.item_id == item.item_id).count()
        result.append({
            "item_id": item.item_id,
            "item_name": item.item_name,
            "abbr": item.abbr,
            "english_name": item.english_name,
            "category": item.category,
            "standard_unit": item.standard_unit,
            "reference_range": item.reference_range,
            "description": item.description,
            "alias_count": alias_count
        })
    
    return ResponseModel(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": result
    })


@router.post("/", response_model=ResponseModel)
async def create_labitem(
    request: LabItemCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if db.query(LabItem).filter(LabItem.item_name == request.item_name).first():
        raise HTTPException(status_code=400, detail="指标名称已存在")
    
    item = LabItem(
        item_name=request.item_name,
        abbr=request.abbr,
        english_name=request.english_name,
        category=request.category,
        standard_unit=request.standard_unit,
        reference_range=request.reference_range,
        description=request.description
    )
    db.add(item)
    
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="CREATE_LABITEM",
        target_table="LabItem",
        target_id=str(item.item_id),
        old_value="",
        new_value=json.dumps(request.dict(), ensure_ascii=False),
    )
    db.add(audit)
    
    db.commit()
    db.refresh(item)
    
    return ResponseModel(data={"item_id": item.item_id})


@router.put("/{item_id}", response_model=ResponseModel)
async def update_labitem(
    item_id: int,
    request: LabItemUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(LabItem).filter(LabItem.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="指标不存在")
    
    old_value = json.dumps({
        "item_name": item.item_name,
        "abbr": item.abbr,
        "english_name": item.english_name,
        "category": item.category,
        "standard_unit": item.standard_unit,
        "reference_range": item.reference_range,
        "description": item.description
    }, ensure_ascii=False)
    
    if request.item_name:
        item.item_name = request.item_name
    if request.abbr is not None:
        item.abbr = request.abbr
    if request.english_name is not None:
        item.english_name = request.english_name
    if request.category is not None:
        item.category = request.category
    if request.standard_unit:
        item.standard_unit = request.standard_unit
    if request.reference_range is not None:
        item.reference_range = request.reference_range
    if request.description is not None:
        item.description = request.description
    
    new_value = json.dumps({
        "item_name": item.item_name,
        "abbr": item.abbr,
        "english_name": item.english_name,
        "category": item.category,
        "standard_unit": item.standard_unit,
        "reference_range": item.reference_range,
        "description": item.description
    }, ensure_ascii=False)
    
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="UPDATE_LABITEM",
        target_table="LabItem",
        target_id=str(item_id),
        old_value=old_value,
        new_value=new_value,
    )
    db.add(audit)
    
    db.commit()
    
    return ResponseModel(data={"item_id": item_id})


@router.delete("/{item_id}", response_model=ResponseModel)
async def delete_labitem(
    item_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(LabItem).filter(LabItem.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="指标不存在")
    
    db.query(Alias).filter(Alias.item_id == item_id).delete()
    
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="DELETE_LABITEM",
        target_table="LabItem",
        target_id=str(item_id),
        old_value=json.dumps({"item_name": item.item_name}, ensure_ascii=False),
        new_value="",
    )
    db.add(audit)
    
    db.delete(item)
    db.commit()
    
    return ResponseModel(data={"item_id": item_id})


@router.get("/{item_id}/aliases", response_model=ResponseModel)
async def get_aliases(
    item_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    aliases = db.query(Alias).filter(Alias.item_id == item_id).all()
    return ResponseModel(data=[{
        "alias_id": a.alias_id,
        "alias_name": a.alias_name
    } for a in aliases])


@router.post("/{item_id}/aliases", response_model=ResponseModel)
async def save_aliases(
    item_id: int,
    request: AliasSaveRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(LabItem).filter(LabItem.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="指标不存在")
    
    db.query(Alias).filter(Alias.item_id == item_id).delete()
    
    for alias_name in request.aliases:
        if alias_name.strip():
            db.add(Alias(item_id=item_id, alias_name=alias_name.strip()))
    
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="UPDATE_ALIAS",
        target_table="Alias",
        target_id=str(item_id),
        old_value="",
        new_value=json.dumps({"aliases": request.aliases}, ensure_ascii=False),
    )
    db.add(audit)
    
    db.commit()
    
    return ResponseModel(data={"item_id": item_id, "count": len(request.aliases)})


@router.post("/sync", response_model=ResponseModel)
async def sync_lab_items(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """手动触发：从已解析报告中同步标准指标库

    - 自动新增报告中出现但标准库中不存在的指标
    - 补全已有指标的参考范围和单位
    """
    from parser.labitem_sync import LabItemSync

    syncer = LabItemSync(db)
    stats = syncer.sync()

    return ResponseModel(data={
        "message": "同步完成",
        **stats,
    })


@router.get("/options", response_model=ResponseModel)
async def get_labitem_options(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    items = db.query(LabItem).order_by(LabItem.item_name).all()
    return ResponseModel(data=[{
        "value": item.item_id,
        "label": f"{item.item_name} ({item.abbr})" if item.abbr else item.item_name
    } for item in items])


@router.get("/export")
async def export_labitems(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    items = db.query(LabItem).order_by(LabItem.item_name).all()
    
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "项目名称", "缩写", "英文名称", "分类", 
        "标准单位", "参考范围", "描述", "别名"
    ])
    
    for item in items:
        aliases = db.query(Alias).filter(Alias.item_id == item.item_id).all()
        alias_names = ";".join([a.alias_name for a in aliases])
        
        writer.writerow([
            item.item_name or "",
            item.abbr or "",
            item.english_name or "",
            item.category or "",
            item.standard_unit or "",
            item.reference_range or "",
            item.description or "",
            alias_names or ""
        ])
    
    output.seek(0)
    
    import urllib.parse
    
    return StreamingResponse(
        output,
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f"attachment; filename*=utf-8''{urllib.parse.quote('标准指标库.csv')}"
        }
    )
