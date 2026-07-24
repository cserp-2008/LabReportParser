from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
import logging
import time
from db.session import get_db
from db.models import UploadTask, AIConfig
from core.security import get_current_user
from core.schemas import ResponseModel
from utils.file_utils import generate_task_id, calculate_md5
from core.config import config
from ai.service import AIService, DEFAULT_PROMPT

router = APIRouter(prefix="/api/v1/ai", tags=["AI识别"])
logger = logging.getLogger(__name__)


@router.get("/config", response_model=ResponseModel)
def get_ai_config(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    service = AIService(db)
    config = service.get_config()
    if config:
        return ResponseModel(data={
            "config_id": config.config_id,
            "api_key": config.api_key[:4] + "****" + config.api_key[-4:] if config.api_key else "",
            "base_url": config.base_url,
            "model_name": config.model_name,
            "prompt": config.prompt,
            "is_active": config.is_active,
            "create_time": config.create_time.strftime("%Y-%m-%d %H:%M:%S") if config.create_time else None,
            "update_time": config.update_time.strftime("%Y-%m-%d %H:%M:%S") if config.update_time else None,
        })
    return ResponseModel(data={
        "prompt": DEFAULT_PROMPT,
        "base_url": "https://ark.cn-beijing.volces.com/api/v3"
    })


@router.post("/config", response_model=ResponseModel)
def save_ai_config(
    api_key: str = Form(...),
    base_url: str = Form(...),
    model_name: str = Form(...),
    prompt: Optional[str] = Form(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AIService(db)
    saved = service.save_config(api_key, base_url, model_name, prompt)
    return ResponseModel(data={
        "config_id": saved.config_id,
        "api_key": saved.api_key[:4] + "****" + saved.api_key[-4:],
        "base_url": saved.base_url,
        "model_name": saved.model_name,
        "is_active": saved.is_active,
        "message": "配置保存成功"
    })


@router.get("/config/test", response_model=ResponseModel)
def test_ai_config(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    service = AIService(db)
    if not service.has_config():
        return ResponseModel(code=400, msg="AI配置未设置")

    try:
        import httpx
        client = httpx.Client(
            base_url=service.config.base_url,
            headers={"Authorization": f"Bearer {service.config.api_key}"},
            timeout=30.0
        )
        response = client.get("/models")
        if response.status_code == 200:
            models = response.json()
            return ResponseModel(data={
                "success": True,
                "message": "API连接成功",
                "available_models": [m.get("id", "") for m in models.get("data", [])]
            })
        else:
            return ResponseModel(code=400, msg=f"API连接失败: {response.status_code}")
    except Exception as e:
        return ResponseModel(code=400, msg=f"测试失败: {str(e)}")


@router.get("/default-prompt", response_model=ResponseModel)
def get_default_prompt():
    return ResponseModel(data={"prompt": DEFAULT_PROMPT})


@router.post("/recognize/file", response_model=ResponseModel)
def ai_recognize_file(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task_id = generate_task_id()

    task = UploadTask(
        task_id=task_id,
        user_id=current_user.user_id,
        file_total=1,
        status=1,
        progress=20,
        success_count=0,
        message="AI识别中"
    )
    db.add(task)
    db.commit()

    temp_path = os.path.join(config['storage_root'], "temp", file.filename)
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    service = AIService(db)
    try:
        task.progress = 50
        db.commit()

        result = service.parse_report(temp_path, task_id, config['storage_root'])

        task.progress = 100
        task.status = 2
        task.success_count = 1
        task.message = "AI识别完成"
        db.commit()

        return ResponseModel(data={
            "task_id": task_id,
            "report_id": result.get("report_id"),
            "patient": result.get("patient"),
            "result_count": result.get("result_count", 0),
            "page_count": result.get("page_count", 0),
            "quality_score": result.get("quality_score", 0),
        })
    except Exception as e:
        logger.error(f"AI识别失败: {e}", exc_info=True)
        task.status = 3
        task.progress = 100
        task.message = f"AI识别失败: {str(e)}"
        db.commit()

        return ResponseModel(code=500, msg=str(e), data={"task_id": task_id})
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


@router.post("/recognize/files", response_model=ResponseModel)
def ai_recognize_files(
    files: List[UploadFile] = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task_id = generate_task_id()

    task = UploadTask(
        task_id=task_id,
        user_id=current_user.user_id,
        file_total=len(files),
        status=1,
        progress=0,
        success_count=0,
        message="AI识别中"
    )
    db.add(task)
    db.commit()

    service = AIService(db)
    report_ids = []
    success_count = 0
    errors = []

    for idx, file in enumerate(files):
        temp_path = os.path.join(config['storage_root'], "temp", file.filename)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)

        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            result = service.parse_report(temp_path, task_id, config['storage_root'])
            report_ids.append(result.get("report_id"))
            success_count += 1
        except Exception as e:
            errors.append({"file_name": file.filename, "error": str(e)})
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

        task.progress = int((idx + 1) / len(files) * 100)
        db.commit()

    task.status = 2
    task.success_count = success_count
    task.message = f"AI识别完成，成功 {success_count}/{len(files)}"
    db.commit()

    return ResponseModel(data={
        "task_id": task_id,
        "report_ids": report_ids,
        "success_count": success_count,
        "error_count": len(errors),
        "errors": errors
    })