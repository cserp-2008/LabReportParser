from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
import logging
import time
from db.session import get_db
from db.models import UploadTask, Report, ReportPage, LabResult
from core.security import get_current_user
from core.schemas import ResponseModel
from utils.file_utils import generate_task_id, generate_report_id, get_storage_path, calculate_md5
from core.config import config
from parser.service import ParseService

router = APIRouter(prefix="/api/v1/upload", tags=["文件上传"])
logger = logging.getLogger(__name__)

def db_retry(func):
    def wrapper(*args, **kwargs):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"数据库锁定，重试第 {attempt + 1}/{max_retries} 次")
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise
    return wrapper


def check_duplicate(db: Session, file_md5: str):
    """检查文件MD5是否已存在于数据库中（未删除的报告）"""
    return db.query(Report).filter(
        Report.file_md5 == file_md5,
        Report.is_delete == 0
    ).first()


def delete_report_and_related(db: Session, report: Report):
    """软删除报告及其关联数据（页面、检验结果）"""
    report_id = report.report_id

    page_ids = [p.page_id for p in db.query(ReportPage).filter(ReportPage.report_id == report_id).all()]
    if page_ids:
        db.query(LabResult).filter(LabResult.page_id.in_(page_ids)).delete(synchronize_session=False)

    db.query(ReportPage).filter(ReportPage.report_id == report_id).delete(synchronize_session=False)

    old_storage_path = report.storage_path
    report.is_delete = 1
    db.flush()

    if old_storage_path and os.path.exists(old_storage_path):
        try:
            os.remove(old_storage_path)
        except Exception as e:
            logger.warning(f"删除旧文件失败 {old_storage_path}: {e}")


@router.post("/file", response_model=ResponseModel)
def upload_file(
    file: UploadFile = File(...),
    overwrite: bool = False,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """单文件上传并解析

    使用同步 def（非 async def），FastAPI 会自动放入线程池执行，
    从而支持多个文件并行上传解析。

    参数:
    - overwrite: 是否覆盖已存在的相同MD5报告（默认False，重复时返回提示）
    """
    task_id = generate_task_id()

    task = UploadTask(
        task_id=task_id,
        user_id=current_user.user_id,
        file_total=1,
        status=1,
        progress=50,
        success_count=0,
        message="上传中"
    )
    db.add(task)
    db.commit()

    report_id = generate_report_id()
    storage_root = config['storage_root']
    storage_path = get_storage_path(storage_root, report_id, file.filename)

    with open(storage_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_md5 = calculate_md5(storage_path)
    file_size = os.path.getsize(storage_path)

    # 重复检测
    existing_report = check_duplicate(db, file_md5)
    if existing_report and not overwrite:
        # 清理临时文件
        try:
            os.remove(storage_path)
        except Exception:
            pass

        task.status = 3
        task.progress = 100
        task.message = "文件已存在"
        db.commit()

        return ResponseModel(code=409, msg="文件已存在，是否覆盖？", data={
            "duplicate": True,
            "existing_report_id": existing_report.report_id,
            "existing_file_name": existing_report.file_name,
            "existing_create_time": existing_report.create_time.strftime("%Y-%m-%d %H:%M:%S") if existing_report.create_time else None,
            "file_md5": file_md5,
            "file_size": file_size,
        })

    # 覆盖旧报告
    if existing_report and overwrite:
        logger.info(f"覆盖报告 {existing_report.report_id} (MD5: {file_md5})")
        delete_report_and_related(db, existing_report)
        db.commit()

    report = Report(
        report_id=report_id,
        task_id=task_id,
        file_name=file.filename,
        file_type=file.filename.split('.')[-1].lower(),
        file_size=file_size,
        file_md5=file_md5,
        storage_path=storage_path,
        page_count=1,
        quality_score=0,
        review_status=0
    )
    db.add(report)
    db.commit()

    # 自动解析报告
    parse_result = None
    parse_steps = []
    parse_error = None
    try:
        service = ParseService(db)
        parse_result = service.parse_report(report)
        logger.info(f"报告解析完成: {parse_result}")
        parse_steps = [
            f"PDF 文本提取完成，共 {parse_result.get('page_count', 0)} 页",
            f"识别医院：{parse_result.get('hospital_id', '未识别') or '未识别'}",
            f"患者信息：{parse_result.get('patient_name', '未知') or '未知'}",
            f"解析指标数：{parse_result.get('result_count', 0)}",
            f"质量评分：{parse_result.get('quality_score', 0)}",
        ]
    except Exception as e:
        logger.error(f"报告解析失败 {report_id}: {e}", exc_info=True)
        parse_error = str(e)

    task.status = 2
    task.progress = 100
    task.success_count = 1 if parse_result else 0
    task.message = "上传并解析成功" if parse_result else "上传成功，解析失败"
    db.commit()

    return ResponseModel(data={
        "task_id": task_id,
        "report_id": report_id,
        "parse_result": parse_result,
        "parse_steps": parse_steps,
        "parse_error": parse_error,
        "file_size": file_size,
        "overwritten": existing_report is not None and overwrite,
    })


@router.post("/files", response_model=ResponseModel)
def upload_files(
    files: List[UploadFile] = File(...),
    overwrite: bool = False,
    current_user = Depends(get_current_user),
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
        message="上传中"
    )
    db.add(task)
    db.commit()

    storage_root = config['storage_root']
    report_ids = []
    success_count = 0
    duplicates = []

    for idx, file in enumerate(files):
        report_id = generate_report_id()
        storage_path = get_storage_path(storage_root, report_id, file.filename)

        with open(storage_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_md5 = calculate_md5(storage_path)
        file_size = os.path.getsize(storage_path)

        # 重复检测
        existing_report = check_duplicate(db, file_md5)
        if existing_report and not overwrite:
            try:
                os.remove(storage_path)
            except Exception:
                pass
            duplicates.append({
                "file_name": file.filename,
                "existing_report_id": existing_report.report_id,
                "existing_file_name": existing_report.file_name,
                "existing_create_time": existing_report.create_time.strftime("%Y-%m-%d %H:%M:%S") if existing_report.create_time else None,
                "file_md5": file_md5,
            })
            task.progress = int((idx + 1) / len(files) * 100)
            continue

        if existing_report and overwrite:
            logger.info(f"覆盖报告 {existing_report.report_id} (MD5: {file_md5})")
            delete_report_and_related(db, existing_report)
            db.commit()

        report = Report(
            report_id=report_id,
            task_id=task_id,
            file_name=file.filename,
            file_type=file.filename.split('.')[-1].lower(),
            file_size=file_size,
            file_md5=file_md5,
            storage_path=storage_path,
            page_count=1,
            quality_score=0,
            review_status=0
        )
        db.add(report)
        db.commit()

        # 自动解析
        try:
            service = ParseService(db)
            service.parse_report(report)
            success_count += 1
        except Exception as e:
            logger.error(f"报告解析失败 {report_id}: {e}", exc_info=True)

        report_ids.append(report_id)
        task.progress = int((idx + 1) / len(files) * 100)

    task.status = 2
    task.progress = 100
    task.success_count = success_count

    if duplicates and not overwrite:
        task.message = f"完成，成功 {success_count}/{len(files)}，{len(duplicates)} 个文件已存在"
        db.commit()
        return ResponseModel(code=409, msg=f"{len(duplicates)} 个文件已存在，是否覆盖？", data={
            "task_id": task_id,
            "report_ids": report_ids,
            "success_count": success_count,
            "duplicates": duplicates,
        })

    task.message = f"完成，成功 {success_count}/{len(files)}"
    db.commit()

    return ResponseModel(data={
        "task_id": task_id,
        "report_ids": report_ids,
        "success_count": success_count
    })
