import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from backend.app.database.connection import Base

class ProjectProfile(Base):
    __tablename__ = "project_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    config = Column(JSON, nullable=False)  # Stores variables, types, core vs optional flags, binary mappings, value labels
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    dataset_name = Column(String, nullable=False)
    profile_name = Column(String, nullable=False)
    upload_timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    validation_timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    username = Column(String, default="DP User")
    result = Column(String, nullable=False)  # PASS, WARNING, FAIL
    score = Column(Float, nullable=False)
    report_xlsx_path = Column(String, nullable=True)
    report_pdf_path = Column(String, nullable=True)
    report_json_path = Column(String, nullable=True)
    summary_data = Column(JSON, nullable=True)  # Stores serialized counts (rows, columns, errors, binary issues, null counts)

class FixAuditLog(Base):
    __tablename__ = "fix_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    validation_id = Column(Integer, nullable=False, index=True)
    original_file = Column(String, nullable=False)
    corrected_file = Column(String, nullable=False)
    fixes_applied_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class MappingReviewLog(Base):
    __tablename__ = "mapping_review_logs"

    id = Column(Integer, primary_key=True, index=True)
    run_session_id = Column(String, index=True, nullable=False)
    validation_id = Column(Integer, nullable=True, index=True)
    dataset_name = Column(String, nullable=True)
    dp_variable = Column(String, nullable=False)
    required = Column(Integer, nullable=False, default=1)
    auto_suggestion = Column(String, nullable=True)
    user_selected_column = Column(String, nullable=True)
    confidence_band = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    match_reason = Column(String, nullable=True)
    user_override = Column(Integer, nullable=False, default=0)
    waived = Column(Integer, nullable=False, default=0)
    waive_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
