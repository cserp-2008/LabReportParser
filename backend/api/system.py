from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from db.session import get_db
from core.security import get_current_user
from core.schemas import ResponseModel
from core.config import config

router = APIRouter(prefix="/api/v1/system", tags=["系统配置"])


class SystemConfig(BaseModel):
    ocr_engine: str = "paddle"
    quality_threshold: int = 80
    max_file_size: int = 20
    max_pages: int = 20
    auto_parse: bool = True
    storage_type: str = "local"
    storage_path: str = "./data/uploads"
    keep_original: bool = True
    session_timeout: int = 120
    min_password_length: int = 6
    max_retry_count: int = 3


@router.get("/config", response_model=ResponseModel)
async def get_system_config(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取系统配置"""
    config_data = {
        "ocr_engine": config.get("ocr_engine", "paddle"),
        "quality_threshold": config.get("quality_threshold", 80),
        "max_file_size": config.get("max_file_size", 20),
        "max_pages": config.get("max_pages", 20),
        "auto_parse": config.get("auto_parse", True),
        "storage_type": config.get("storage_type", "local"),
        "storage_path": config.get("storage_path", "./data/uploads"),
        "keep_original": config.get("keep_original", True),
        "session_timeout": config.get("session_timeout", 120),
        "min_password_length": config.get("min_password_length", 6),
        "max_retry_count": config.get("max_retry_count", 3),
        "api_port": config.get("api_port", 8000),
        "secret_key": "******",
    }
    
    return ResponseModel(data=config_data)


@router.post("/config", response_model=ResponseModel)
async def save_system_config(
    request: SystemConfig,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """保存系统配置"""
    config.update({
        "ocr_engine": request.ocr_engine,
        "quality_threshold": request.quality_threshold,
        "max_file_size": request.max_file_size,
        "max_pages": request.max_pages,
        "auto_parse": request.auto_parse,
        "storage_type": request.storage_type,
        "storage_path": request.storage_path,
        "keep_original": request.keep_original,
        "session_timeout": request.session_timeout,
        "min_password_length": request.min_password_length,
        "max_retry_count": request.max_retry_count,
    })
    
    import json
    config_path = "./config.json"
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    
    return ResponseModel(data={"message": "配置保存成功"})


@router.get("/info", response_model=ResponseModel)
async def get_system_info(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取系统信息"""
    import platform
    import sys
    
    info = {
        "version": "3.0.0",
        "platform": platform.system(),
        "python_version": sys.version.split()[0],
        "architecture": platform.architecture()[0],
        "hostname": platform.node(),
    }
    
    return ResponseModel(data=info)
