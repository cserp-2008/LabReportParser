from db.models_simple import Base, User, Role, UserRole, LabItem, Alias
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.security import get_password_hash
from datetime import datetime

# 使用 SQLite
DATABASE_URL = "sqlite:///./labreport.db"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建表
Base.metadata.create_all(bind=engine)

# 初始化数据
db = SessionLocal()

try:
    # 检查是否已有数据
    if db.query(User).count() == 0:
        # 创建默认管理员用户 (admin/admin123)
        admin = User(
            username="admin",
            password=get_password_hash("admin123"),
            real_name="系统管理员",
            is_enable=True,
            create_time=datetime.now()
        )
        db.add(admin)
        db.flush()

        # 创建默认角色
        admin_role = Role(
            role_name="admin",
            permission_list='["*"]'
        )
        user_role = Role(
            role_name="user",
            permission_list='["report:view", "report:upload", "result:view"]'
        )
        db.add(admin_role)
        db.add(user_role)
        db.flush()

        # 分配角色
        user_role_link = UserRole(
            user_id=admin.user_id,
            role_id=admin_role.role_id
        )
        db.add(user_role_link)

        # 初始化标准检验项目
        lab_items = [
            LabItem(item_name="白细胞计数", abbr="WBC", english_name="White Blood Cell", category="血常规", standard_unit="×10⁹/L"),
            LabItem(item_name="红细胞计数", abbr="RBC", english_name="Red Blood Cell", category="血常规", standard_unit="×10¹²/L"),
            LabItem(item_name="血红蛋白", abbr="HGB", english_name="Hemoglobin", category="血常规", standard_unit="g/L"),
            LabItem(item_name="红细胞压积", abbr="HCT", english_name="Hematocrit", category="血常规", standard_unit="%"),
            LabItem(item_name="平均红细胞体积", abbr="MCV", english_name="Mean Corpuscular Volume", category="血常规", standard_unit="fL"),
            LabItem(item_name="血小板计数", abbr="PLT", english_name="Platelet", category="血常规", standard_unit="×10⁹/L"),
            LabItem(item_name="谷丙转氨酶", abbr="ALT", english_name="Alanine Aminotransferase", category="肝功能", standard_unit="U/L"),
            LabItem(item_name="谷草转氨酶", abbr="AST", english_name="Aspartate Aminotransferase", category="肝功能", standard_unit="U/L"),
            LabItem(item_name="总胆红素", abbr="TBIL", english_name="Total Bilirubin", category="肝功能", standard_unit="μmol/L"),
            LabItem(item_name="肌酐", abbr="Cr", english_name="Creatinine", category="肾功能", standard_unit="μmol/L"),
            LabItem(item_name="尿素氮", abbr="BUN", english_name="Blood Urea Nitrogen", category="肾功能", standard_unit="mmol/L"),
            LabItem(item_name="尿酸", abbr="UA", english_name="Uric Acid", category="肾功能", standard_unit="μmol/L"),
            LabItem(item_name="空腹血糖", abbr="FBG", english_name="Fasting Blood Glucose", category="血糖", standard_unit="mmol/L"),
            LabItem(item_name="甘油三酯", abbr="TG", english_name="Triglyceride", category="血脂", standard_unit="mmol/L"),
            LabItem(item_name="总胆固醇", abbr="TC", english_name="Total Cholesterol", category="血脂", standard_unit="mmol/L"),
            LabItem(item_name="高密度脂蛋白胆固醇", abbr="HDL-C", english_name="High-Density Lipoprotein Cholesterol", category="血脂", standard_unit="mmol/L"),
            LabItem(item_name="低密度脂蛋白胆固醇", abbr="LDL-C", english_name="Low-Density Lipoprotein Cholesterol", category="血脂", standard_unit="mmol/L"),
        ]
        for item in lab_items:
            db.add(item)
        db.flush()

        # 初始化别名
        aliases = [
            Alias(item_id=1, alias_name="白细胞"),
            Alias(item_id=1, alias_name="WBC"),
            Alias(item_id=2, alias_name="红细胞"),
            Alias(item_id=2, alias_name="RBC"),
            Alias(item_id=3, alias_name="血色素"),
            Alias(item_id=3, alias_name="HGB"),
            Alias(item_id=7, alias_name="丙氨酸氨基转移酶"),
            Alias(item_id=7, alias_name="GPT"),
            Alias(item_id=8, alias_name="天门冬氨酸氨基转移酶"),
            Alias(item_id=8, alias_name="GOT"),
        ]
        for alias in aliases:
            db.add(alias)

        db.commit()
        print("数据库初始化完成！")
    else:
        print("数据库已有数据，跳过初始化。")
except Exception as e:
    db.rollback()
    print(f"初始化失败: {e}")
finally:
    db.close()
