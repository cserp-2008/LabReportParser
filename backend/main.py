import sys
import os
import logging
from contextlib import asynccontextmanager

# 禁止写入 .pyc 缓存文件，避免 Trae 沙箱限制
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# 确保当前目录优先于其他 site-packages 中的同名包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import auth, report, upload, preview, trend, review, stats, export, task, hospital, labitem, user, system, ai
from core.config import config
from db.session import engine, SessionLocal
from db.models import Base, User, Role, UserRole, LabItem, Alias, Hospital

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化"""
    Base.metadata.create_all(bind=engine)
    _migrate_db()
    _init_seed_data()

    import threading
    t = threading.Thread(target=_parse_existing_reports, daemon=True)
    t.start()
    yield


app = FastAPI(title="LabReportParser API", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(report.router)
app.include_router(upload.router)
app.include_router(preview.router)
app.include_router(trend.router)
app.include_router(review.router)
app.include_router(stats.router)
app.include_router(export.router)
app.include_router(task.router)
app.include_router(hospital.router)
app.include_router(labitem.router)
app.include_router(user.router)
app.include_router(system.router)
app.include_router(ai.router)


def _migrate_db():
    """数据库迁移：添加新字段到已有表"""
    from sqlalchemy import text, inspect

    inspector = inspect(engine)
    if not inspector.has_table("Hospital"):
        return

    existing_columns = [c["name"] for c in inspector.get_columns("Hospital")]
    if "template_config" not in existing_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE Hospital ADD COLUMN template_config TEXT"))
            conn.commit()
        logger.info("已添加 Hospital.template_config 字段")

    # LabItem 表添加 reference_range 字段
    if inspector.has_table("LabItem"):
        labitem_columns = [c["name"] for c in inspector.get_columns("LabItem")]
        if "reference_range" not in labitem_columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE LabItem ADD COLUMN reference_range VARCHAR(100)"))
                conn.commit()
            logger.info("已添加 LabItem.reference_range 字段")


def _init_seed_data():
    """初始化基础数据：管理员用户、角色、标准检验项目"""
    from core.security import get_password_hash
    from datetime import datetime

    db = SessionLocal()
    try:
        # 初始化管理员
        if db.query(User).count() == 0:
            admin = User(
                username="admin",
                password=get_password_hash("admin123"),
                real_name="系统管理员",
                is_enable=True,
            )
            db.add(admin)
            db.flush()

            admin_role = Role(role_name="admin", permission_list='["*"]')
            user_role = Role(role_name="user", permission_list='["report:view","report:upload","result:view"]')
            db.add(admin_role)
            db.add(user_role)
            db.flush()

            db.add(UserRole(user_id=admin.user_id, role_id=admin_role.role_id))

            # 初始化标准检验项目
            lab_items = [
                LabItem(item_name="白细胞计数", abbr="WBC", english_name="White Blood Cell", category="血常规", standard_unit="×10⁹/L", reference_range="3.5-9.5"),
                LabItem(item_name="红细胞计数", abbr="RBC", english_name="Red Blood Cell", category="血常规", standard_unit="×10¹²/L", reference_range="男:4.3-5.8;女:3.8-5.1"),
                LabItem(item_name="血红蛋白", abbr="HGB", english_name="Hemoglobin", category="血常规", standard_unit="g/L", reference_range="男:130-175;女:115-150"),
                LabItem(item_name="红细胞压积", abbr="HCT", english_name="Hematocrit", category="血常规", standard_unit="%", reference_range="男:40-50;女:35-45"),
                LabItem(item_name="平均红细胞体积", abbr="MCV", english_name="Mean Corpuscular Volume", category="血常规", standard_unit="fL", reference_range="82-100"),
                LabItem(item_name="血小板计数", abbr="PLT", english_name="Platelet", category="血常规", standard_unit="×10⁹/L", reference_range="125-350"),
                LabItem(item_name="谷丙转氨酶", abbr="ALT", english_name="Alanine Aminotransferase", category="肝功能", standard_unit="U/L", reference_range="9-50"),
                LabItem(item_name="谷草转氨酶", abbr="AST", english_name="Aspartate Aminotransferase", category="肝功能", standard_unit="U/L", reference_range="15-40"),
                LabItem(item_name="总胆红素", abbr="TBIL", english_name="Total Bilirubin", category="肝功能", standard_unit="μmol/L", reference_range="5.1-28.0"),
                LabItem(item_name="肌酐", abbr="Cr", english_name="Creatinine", category="肾功能", standard_unit="μmol/L", reference_range="男:57-97;女:41-73"),
                LabItem(item_name="尿素氮", abbr="BUN", english_name="Blood Urea Nitrogen", category="肾功能", standard_unit="mmol/L", reference_range="2.9-8.2"),
                LabItem(item_name="尿酸", abbr="UA", english_name="Uric Acid", category="肾功能", standard_unit="μmol/L", reference_range="男:208-428;女:155-357"),
                LabItem(item_name="空腹血糖", abbr="FBG", english_name="Fasting Blood Glucose", category="血糖", standard_unit="mmol/L", reference_range="3.9-6.1"),
                LabItem(item_name="甘油三酯", abbr="TG", english_name="Triglyceride", category="血脂", standard_unit="mmol/L", reference_range="0.45-1.81"),
                LabItem(item_name="总胆固醇", abbr="TC", english_name="Total Cholesterol", category="血脂", standard_unit="mmol/L", reference_range="<5.2"),
                LabItem(item_name="高密度脂蛋白胆固醇", abbr="HDL-C", english_name="High-Density Lipoprotein Cholesterol", category="血脂", standard_unit="mmol/L", reference_range=">1.04"),
                LabItem(item_name="低密度脂蛋白胆固醇", abbr="LDL-C", english_name="Low-Density Lipoprotein Cholesterol", category="血脂", standard_unit="mmol/L", reference_range="<3.4"),
            ]
            for item in lab_items:
                db.add(item)
            db.flush()

            aliases = [
                Alias(item_id=1, alias_name="白细胞"), Alias(item_id=1, alias_name="WBC"),
                Alias(item_id=2, alias_name="红细胞"), Alias(item_id=2, alias_name="RBC"),
                Alias(item_id=3, alias_name="血色素"), Alias(item_id=3, alias_name="HGB"),
                Alias(item_id=7, alias_name="丙氨酸氨基转移酶"), Alias(item_id=7, alias_name="GPT"),
                Alias(item_id=8, alias_name="天门冬氨酸氨基转移酶"), Alias(item_id=8, alias_name="GOT"),
            ]
            for alias in aliases:
                db.add(alias)

            db.commit()
            logger.info("基础数据初始化完成")
        else:
            logger.info("基础数据已存在，跳过初始化")

        # 自动同步标准指标库：从已解析报告中学习新指标和参考范围
        _sync_lab_items(db)
    except Exception as e:
        db.rollback()
        logger.error(f"初始化数据失败: {e}")
    finally:
        db.close()


def _sync_lab_items(db):
    """从已解析报告中同步标准指标库"""
    try:
        from parser.labitem_sync import LabItemSync
        syncer = LabItemSync(db)
        stats = syncer.sync()
        if stats["new_items"] or stats["updated_ref"] or stats["updated_unit"]:
            logger.info(
                f"标准指标库同步完成: 新增指标 {stats['new_items']} 个, "
                f"补全参考范围 {stats['updated_ref']} 个, "
                f"补全单位 {stats['updated_unit']} 个"
            )
    except Exception as e:
        logger.error(f"标准指标库同步失败: {e}")


def _parse_existing_reports():
    """解析已有但未解析的报告（无 LabResult 记录的报告）"""
    from db.models import Report, LabResult
    from parser.service import ParseService
    import time

    db = SessionLocal()
    try:
        # 查找没有任何检验结果的报告（而非 quality_score == 0，
        # 因为大便常规、血型等非生化报告的 quality_score 始终为 0 但已解析成功）
        parsed_report_ids = db.query(LabResult.report_id).distinct().subquery()
        unparsed = db.query(Report).filter(
            Report.is_delete == 0,
            ~Report.report_id.in_(parsed_report_ids)
        ).all()
        if not unparsed:
            return
        logger.info(f"发现 {len(unparsed)} 个未解析报告，开始解析...")
        service = ParseService(db)
        for report in unparsed:
            try:
                result = service.parse_report(report)
                logger.info(f"解析报告 {report.report_id}: {result['result_count']} 条指标")
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"解析报告 {report.report_id} 失败: {e}")
            time.sleep(1)
    except Exception as e:
        logger.error(f"启动解析失败: {e}")
    finally:
        db.close()


@app.get("/")
async def root():
    return {"message": "LabReportParser API Server", "version": "3.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config['api_port'])
