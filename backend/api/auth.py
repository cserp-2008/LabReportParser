from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import User
from core.security import verify_password, create_access_token, get_current_user
from core.schemas import LoginRequest, TokenData, ResponseModel, UserInfo

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.post("/login", response_model=ResponseModel)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    if not user.is_enable:
        raise HTTPException(status_code=400, detail="用户已禁用")
    
    access_token = create_access_token(data={"sub": user.username})
    return ResponseModel(data={"access_token": access_token, "token_type": "bearer"})


@router.get("/me", response_model=ResponseModel)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    user_info = UserInfo(
        user_id=current_user.user_id,
        username=current_user.username,
        real_name=current_user.real_name
    )
    return ResponseModel(data=user_info)
