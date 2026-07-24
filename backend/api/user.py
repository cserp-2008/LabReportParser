from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import json
from db.session import get_db
from db.models import User, Role, UserRole, AuditLog
from core.security import get_current_user, get_password_hash
from core.schemas import ResponseModel

router = APIRouter(prefix="/api/v1/user", tags=["用户管理"])


class UserCreateRequest(BaseModel):
    username: str
    real_name: str
    password: str


class UserUpdateRequest(BaseModel):
    real_name: Optional[str] = None


class RoleAssignRequest(BaseModel):
    roles: List[str]


class ResetPasswordRequest(BaseModel):
    password: str


@router.get("/list", response_model=ResponseModel)
async def get_user_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    
    if keyword:
        query = query.filter(
            (User.username.like(f"%{keyword}%")) |
            (User.real_name.like(f"%{keyword}%"))
        )
    
    total = query.count()
    users = query.order_by(User.create_time.desc()).offset((page-1)*page_size).limit(page_size).all()
    
    result = []
    for user in users:
        user_roles = db.query(Role).join(
            UserRole, UserRole.role_id == Role.role_id
        ).filter(UserRole.user_id == user.user_id).all()
        result.append({
            "user_id": user.user_id,
            "username": user.username,
            "real_name": user.real_name,
            "is_enable": user.is_enable,
            "roles": [r.role_name for r in user_roles],
            "create_time": user.create_time
        })
    
    return ResponseModel(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": result
    })


@router.post("/", response_model=ResponseModel)
async def create_user(
    request: UserCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    user = User(
        username=request.username,
        password=get_password_hash(request.password),
        real_name=request.real_name,
        is_enable=True
    )
    db.add(user)
    
    user_role = db.query(Role).filter(Role.role_name == 'user').first()
    if user_role:
        db.add(UserRole(user_id=user.user_id, role_id=user_role.role_id))
    
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="CREATE_USER",
        target_table="User",
        target_id=str(user.user_id),
        old_value="",
        new_value=json.dumps({"username": request.username, "real_name": request.real_name}, ensure_ascii=False),
    )
    db.add(audit)
    
    db.commit()
    db.refresh(user)
    
    return ResponseModel(data={"user_id": user.user_id})


@router.put("/{user_id}", response_model=ResponseModel)
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    old_value = json.dumps({"real_name": user.real_name}, ensure_ascii=False)
    
    if request.real_name:
        user.real_name = request.real_name
    
    new_value = json.dumps({"real_name": user.real_name}, ensure_ascii=False)
    
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="UPDATE_USER",
        target_table="User",
        target_id=str(user_id),
        old_value=old_value,
        new_value=new_value,
    )
    db.add(audit)
    
    db.commit()
    
    return ResponseModel(data={"user_id": user_id})


@router.post("/{user_id}/roles", response_model=ResponseModel)
async def assign_roles(
    user_id: int,
    request: RoleAssignRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    db.query(UserRole).filter(UserRole.user_id == user_id).delete()
    
    for role_name in request.roles:
        role = db.query(Role).filter(Role.role_name == role_name).first()
        if role:
            db.add(UserRole(user_id=user_id, role_id=role.role_id))
    
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="ASSIGN_ROLE",
        target_table="UserRole",
        target_id=str(user_id),
        old_value="",
        new_value=json.dumps({"roles": request.roles}, ensure_ascii=False),
    )
    db.add(audit)
    
    db.commit()
    
    return ResponseModel(data={"user_id": user_id, "roles": request.roles})


@router.post("/{user_id}/reset-password", response_model=ResponseModel)
async def reset_password(
    user_id: int,
    request: ResetPasswordRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.password = get_password_hash(request.password)
    
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="RESET_PASSWORD",
        target_table="User",
        target_id=str(user_id),
        old_value="",
        new_value=json.dumps({"action": "password_reset"}, ensure_ascii=False),
    )
    db.add(audit)
    
    db.commit()
    
    return ResponseModel(data={"user_id": user_id})


@router.post("/{user_id}/toggle", response_model=ResponseModel)
async def toggle_enable(
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    old_status = user.is_enable
    user.is_enable = 1 - user.is_enable
    
    audit = AuditLog(
        operate_user_id=current_user.user_id,
        operate_type="TOGGLE_USER",
        target_table="User",
        target_id=str(user_id),
        old_value=json.dumps({"is_enable": old_status}, ensure_ascii=False),
        new_value=json.dumps({"is_enable": user.is_enable}, ensure_ascii=False),
    )
    db.add(audit)
    
    db.commit()
    
    return ResponseModel(data={"user_id": user_id, "is_enable": user.is_enable})
