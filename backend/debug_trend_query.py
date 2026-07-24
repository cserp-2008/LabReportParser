from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import LabResult, LabItem, Report, Hospital

DATABASE_URL = "sqlite:///./labreport.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = SessionLocal()

item_id = 37

query = db.query(LabResult, Report).filter(
    LabResult.item_id == item_id,
    LabResult.report_id == Report.report_id,
    Report.is_delete == 0
)

query_results = query.order_by(Report.sample_time).all()
print(f"查询结果数量: {len(query_results)}")

print("\n查询结果详情:")
for i, (result, report) in enumerate(query_results):
    hospital = db.query(Hospital).filter(Hospital.hospital_id == report.hospital_id).first()
    print(f"{i+1}. time={report.sample_time}, value={result.value_numeric}, hospital={hospital.hospital_name if hospital else None}, report_id={report.report_id[:20]}, file_name={report.file_name[:30]}")

db.close()
