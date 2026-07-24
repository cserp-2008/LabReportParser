import hashlib
import os
import uuid
from datetime import datetime


def calculate_md5(file_path: str) -> str:
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def generate_report_id() -> str:
    return str(uuid.uuid4()).replace('-', '')


def generate_task_id() -> str:
    return str(uuid.uuid4()).replace('-', '')


def get_storage_path(storage_root: str, report_id: str, filename: str) -> str:
    date_str = datetime.now().strftime("%Y/%m")
    dir_path = os.path.join(storage_root, "report", date_str)
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, f"{report_id}_{filename}")


def get_preview_path(storage_root: str, report_id: str, page_no: int) -> str:
    dir_path = os.path.join(storage_root, "preview", report_id)
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, f"page_{page_no}.png")


def get_thumbnail_path(storage_root: str, report_id: str) -> str:
    dir_path = os.path.join(storage_root, "thumbnail")
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, f"{report_id}.jpg")


def get_ocr_cache_path(storage_root: str, report_id: str, page_no: int) -> str:
    dir_path = os.path.join(storage_root, "ocr", report_id)
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, f"page_{page_no}.json")
