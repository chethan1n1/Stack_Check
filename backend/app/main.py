import os
import shutil
import uuid
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from backend.app.config import settings
from backend.app.database.connection import engine, Base, get_db
from backend.app.database.models import ProjectProfile, AuditLog, FixAuditLog, MappingReviewLog
from backend.app.schemas.profile import ProjectProfileCreate, ProjectProfileResponse
from backend.app.schemas.validation import ValidationResponseSchema
from pydantic import BaseModel
from backend.app.services.validation_service import ValidationService
from backend.app.services.mapping_review_service import MappingReviewService
from backend.app.parsers.data_parser import DataParser

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

# In-memory review sessions for mapping confirmation step.
MAPPING_REVIEW_SESSIONS: dict[str, dict] = {}

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root Endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to StackCheck DP Data Validation API", "status": "running"}

# -------------------------------------------------------------
# FILE UPLOAD ENDPOINT
# -------------------------------------------------------------
@app.post("/api/v1/upload")
async def upload_files(
    dataset: UploadFile = File(...),
    spec: Optional[UploadFile] = File(None)
):
    """
    Saves uploaded files to the uploads directory.
    Returns:
        dict: Paths of the uploaded files on the local filesystem.
    """
    try:
        # Save dataset
        dataset_path = os.path.join(settings.UPLOAD_DIR, dataset.filename)
        with open(dataset_path, "wb") as buffer:
            shutil.copyfileobj(dataset.file, buffer)
            
        spec_path = None
        if spec:
            spec_path = os.path.join(settings.UPLOAD_DIR, spec.filename)
            with open(spec_path, "wb") as buffer:
                shutil.copyfileobj(spec.file, buffer)
                
        return {
            "dataset_filename": dataset.filename,
            "dataset_path": dataset_path,
            "spec_filename": spec.filename if spec else None,
            "spec_path": spec_path
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload files: {str(e)}"
        )

# -------------------------------------------------------------
# VALIDATION EXECUTION ENDPOINT
# -------------------------------------------------------------
@app.post("/api/v1/validate", response_model=ValidationResponseSchema)
async def validate_dataset(
    dataset_path: str = Form(...),
    profile_id: Optional[int] = Form(None),
    spec_path: Optional[str] = Form(None),
    mapping_id: Optional[str] = Form(None),
    username: str = Form("DP User"),
    db: Session = Depends(get_db)
):
    """
    Runs validation on an uploaded dataset file against a profile configuration or reference spec.
    """
    if not os.path.exists(dataset_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset file not found at: {dataset_path}"
        )
        
    profile_config = None
    profile_name = "Ad-hoc validation"
    
    if profile_id:
        profile = db.query(ProjectProfile).filter(ProjectProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project profile with ID {profile_id} not found."
            )
        profile_config = profile.config
        profile_name = profile.name
        
    if spec_path and not os.path.exists(spec_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specification file not found at: {spec_path}"
        )

    # Apply confirmed mapping session if provided.
    if mapping_id:
        mapping_session = MAPPING_REVIEW_SESSIONS.get(mapping_id)
        if not mapping_session:
            raise HTTPException(status_code=404, detail="Mapping session not found. Please run precheck again.")
        if mapping_session.get("dataset_path") != dataset_path:
            raise HTTPException(status_code=400, detail="Mapping session dataset does not match validation dataset.")
        unresolved_required = (mapping_session.get("mapping_diagnostics") or {}).get("unresolved_required", [])
        if unresolved_required:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Validation blocked: required DP variables are unresolved.",
                    "unresolved_required": unresolved_required,
                },
            )
        profile_config = mapping_session.get("mapped_profile_config") or profile_config

    try:
        # Run validation
        mapping_review_payload = None
        if mapping_id and mapping_session:
            mapping_review_payload = {
                "mapping_id": mapping_id,
                "summary": mapping_session.get("decision_summary", {}),
                "decisions": mapping_session.get("decision_rows", []),
                "diagnostics": mapping_session.get("mapping_diagnostics", {}),
            }

        results = ValidationService.run_validation(
            dataset_path=dataset_path,
            profile_config=profile_config,
            spec_path=spec_path,
            mapping_review=mapping_review_payload,
        )
        
        # Save to Audit Log in DB
        audit_log = AuditLog(
            dataset_name=os.path.basename(dataset_path),
            profile_name=profile_name,
            username=username,
            result=results["final_status"],
            score=results["quality_score"]["score"],
            report_xlsx_path=results["report_xlsx_url"],
            report_pdf_path=results["report_pdf_url"],
            report_json_path=results["report_json_url"],
            summary_data={
                "rows": results["metadata"]["rows"],
                "columns": results["metadata"]["columns"],
                "coverage_pct": results["master_validation"]["coverage_pct"],
                "missing_vars": results["master_validation"]["missing_count"],
                "binary_warnings": results["binary_validation"]["warning_count"],
                "binary_fails": results["binary_validation"]["fail_count"],
                "null_red_count": results["null_analysis"]["red_count"],
                "mapping_summary": (results.get("mapping_review") or {}).get("summary", {}),
            }
        )
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)

        if mapping_id and mapping_session:
            for decision in mapping_session.get("decision_rows", []):
                db.add(
                    MappingReviewLog(
                        run_session_id=mapping_id,
                        validation_id=audit_log.id,
                        dataset_name=os.path.basename(dataset_path),
                        dp_variable=decision.get("dp_variable", ""),
                        required=1 if decision.get("required") else 0,
                        auto_suggestion=decision.get("auto_suggestion"),
                        user_selected_column=decision.get("selected_column"),
                        confidence_band=decision.get("confidence_band"),
                        confidence_score=float(decision.get("confidence_score", 0.0) or 0.0),
                        match_reason=decision.get("match_reason"),
                        user_override=1 if decision.get("user_override") else 0,
                        waived=1 if decision.get("waived") else 0,
                        waive_reason=decision.get("waive_reason"),
                    )
                )
            db.commit()
        
        # Add DB audit ID to response
        results["id"] = audit_log.id
        
        return results
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


class ManuallyAddedVariable(BaseModel):
    dp_variable: str
    required: bool

class ConfirmMappingRequest(BaseModel):
    mapping_id: str
    overrides: dict[str, Optional[str]]
    waivers: Optional[dict[str, str]] = None
    required_overrides: Optional[dict[str, bool]] = None
    block_on_required_unresolved: bool = True
    manually_added_variables: Optional[list[ManuallyAddedVariable]] = None


@app.post("/api/v1/precheck-mapping")
async def precheck_mapping(
    dataset_path: str = Form(...),
    profile_id: Optional[int] = Form(None),
    spec_path: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Runs a fast matching precheck between DP variables and dataset columns.
    This endpoint does not run full validation.
    """
    if not os.path.exists(dataset_path):
        raise HTTPException(status_code=404, detail=f"Dataset file not found at: {dataset_path}")

    profile_config = None
    if profile_id:
        profile = db.query(ProjectProfile).filter(ProjectProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail=f"Project profile with ID {profile_id} not found.")
        profile_config = profile.config
    elif spec_path:
        if not os.path.exists(spec_path):
            raise HTTPException(status_code=404, detail=f"Specification file not found at: {spec_path}")
        profile_config = DataParser.parse_specification_sheet(spec_path)
    else:
        profile_config = {"variables": []}

    df, dataset_meta = DataParser.parse_dataset(dataset_path)
    dataset_candidates = dataset_meta.get("column_candidates") or [
        {"name": str(c), "type_hint": str(df[c].dtype)} for c in df.columns
    ]
    preview = MappingReviewService.build_mapping_preview(profile_config, dataset_candidates)

    mapping_id = str(uuid.uuid4())
    suggested_mapping = {item["dp_variable"]: item.get("suggested_column") for item in preview["items"] if item.get("suggested_column")}

    decision_rows = MappingReviewService.build_decision_rows(preview, suggested_mapping, {})
    decision_summary = MappingReviewService.build_summary(decision_rows)

    MAPPING_REVIEW_SESSIONS[mapping_id] = {
        "dataset_path": dataset_path,
        "profile_config": profile_config,
        "preview": preview,
        "dataset_columns": [c["name"] for c in dataset_candidates],
        "dataset_candidates": dataset_candidates,
        "suggested_mapping": suggested_mapping,
        "waivers": {},
        "decision_rows": decision_rows,
        "decision_summary": decision_summary,
        "mapping_diagnostics": {
            "unresolved_required": [r["dp_variable"] for r in decision_rows if r.get("required") and r.get("status") == "UNMATCHED"],
            "unresolved_optional": [r["dp_variable"] for r in decision_rows if (not r.get("required")) and r.get("status") == "UNMATCHED"],
        },
        "mapped_profile_config": MappingReviewService.apply_confirmed_mapping(profile_config, suggested_mapping),
    }

    return {
        "mapping_id": mapping_id,
        "dataset_path": dataset_path,
        "preview": preview,
        "suggested_mapping": suggested_mapping,
        "waivers": {},
        "summary": decision_summary,
        "mapping_diagnostics": MAPPING_REVIEW_SESSIONS[mapping_id]["mapping_diagnostics"],
        "dataset_candidates": dataset_candidates,
    }


@app.post("/api/v1/confirm-mapping")
async def confirm_mapping(payload: ConfirmMappingRequest):
    """
    Confirms/overrides mapping choices from precheck and stores mapped profile config for validation.
    """
    session = MAPPING_REVIEW_SESSIONS.get(payload.mapping_id)
    if not session:
        raise HTTPException(status_code=404, detail="Mapping session not found.")

    # Add manually added variables to profile_config if provided
    profile_config = session.get("profile_config", {})
    if payload.manually_added_variables:
        if "variables" not in profile_config:
            profile_config["variables"] = []
        for manual_var in payload.manually_added_variables:
            # Check if variable already exists
            existing = [v for v in profile_config["variables"] if v.get("name") == manual_var.dp_variable]
            if not existing:
                profile_config["variables"].append({
                    "name": manual_var.dp_variable,
                    "required": manual_var.required,
                })
    required_overrides = payload.required_overrides or {}
    if required_overrides:
        if "variables" not in profile_config:
            profile_config["variables"] = []
        for var in profile_config["variables"]:
            var_name = var.get("name")
            if var_name in required_overrides:
                var["required"] = bool(required_overrides[var_name])

        # Keep preview required flags in sync for decision diagnostics.
        preview = dict(session.get("preview", {}))
        preview_items = preview.get("items", [])
        for item in preview_items:
            dp_var = item.get("dp_variable")
            if dp_var in required_overrides:
                item["required"] = bool(required_overrides[dp_var])
        preview["items"] = preview_items
        session["preview"] = preview

    session["profile_config"] = profile_config

    suggested = dict(session.get("suggested_mapping", {}))
    dataset_columns = set(session.get("dataset_columns", []))
    for dp_var, mapped_col in (payload.overrides or {}).items():
        if mapped_col:
            if mapped_col not in dataset_columns:
                raise HTTPException(status_code=400, detail=f"Invalid mapping: column '{mapped_col}' does not exist in dataset.")
            suggested[dp_var] = mapped_col
        elif dp_var in suggested:
            del suggested[dp_var]

    waivers = payload.waivers or {}
    decision_rows = MappingReviewService.build_decision_rows(session.get("preview", {}), suggested, waivers)
    summary = MappingReviewService.build_summary(decision_rows)
    unresolved_required_vars = [
        r["dp_variable"]
        for r in decision_rows
        if r.get("required") and r.get("status") == "UNMATCHED"
    ]

    if payload.block_on_required_unresolved and unresolved_required_vars:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Required DP variables are unresolved. Resolve or waive before continuing.",
                "unresolved_required": unresolved_required_vars,
                "summary": summary,
            },
        )

    mapped_profile_config = MappingReviewService.apply_confirmed_mapping(session["profile_config"], suggested, waivers)
    session["suggested_mapping"] = suggested
    session["waivers"] = waivers
    session["decision_rows"] = decision_rows
    session["decision_summary"] = summary
    session["mapping_diagnostics"] = {
        "unresolved_required": unresolved_required_vars,
        "unresolved_optional": [
            r["dp_variable"]
            for r in decision_rows
            if (not r.get("required")) and r.get("status") == "UNMATCHED"
        ],
        "mismatch_diagnostics": [
            {
                "dp_variable": r["dp_variable"],
                "selected_column": r.get("selected_column"),
                "auto_suggestion": r.get("auto_suggestion"),
                "confidence_band": r.get("confidence_band"),
                "reason": r.get("match_reason"),
                "status": r.get("status"),
            }
            for r in decision_rows
        ],
    }
    session["mapped_profile_config"] = mapped_profile_config

    return {
        "mapping_id": payload.mapping_id,
        "confirmed_mapping": suggested,
        "waivers": waivers,
        "summary": summary,
        "mapping_diagnostics": session["mapping_diagnostics"],
    }

# -------------------------------------------------------------
# AUTO-FIX EXECUTION ENDPOINT
# -------------------------------------------------------------
class AutoFixRequest(BaseModel):
    report_id: int
    variables: List[str]

@app.post("/api/v1/auto-fix")
async def auto_fix_dataset(
    payload: AutoFixRequest,
    db: Session = Depends(get_db)
):
    """
    Applies selective auto-fixes to the source dataset, updates audit logs,
    and returns the download link for the corrected file.
    """
    import datetime
    
    audit = db.query(AuditLog).filter(AuditLog.id == payload.report_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit validation report not found.")
        
    # Locate original dataset file in uploads folder
    original_filename = audit.dataset_name
    original_path = os.path.join(settings.UPLOAD_DIR, original_filename)
    
    if not os.path.exists(original_path):
        raise HTTPException(
            status_code=404, 
            detail=f"Original dataset file '{original_filename}' was not found on server storage."
        )
        
    # Load JSON report to read binary warnings
    report_filename = os.path.basename(audit.report_json_path) if audit.report_json_path else None
    if not report_filename:
        raise HTTPException(status_code=404, detail="JSON report file path is missing from audit log.")
        
    json_path = os.path.join(settings.REPORT_DIR, report_filename)
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail=f"Detailed validation report JSON file not found.")
        
    with open(json_path, "r", encoding="utf-8") as f:
        report_data = json.load(f)
        
    binary_issues = report_data.get("binary_validation", {}).get("issues", [])
    
    # Establish corrected filename: e.g. tracker_fixed.sav
    name, ext = os.path.splitext(original_filename)
    corrected_filename = f"{name}_fixed{ext}"
    corrected_path = os.path.join(settings.REPORT_DIR, corrected_filename)
    
    # Apply recoding via AutoFixService
    from backend.app.services.auto_fix_service import AutoFixService
    try:
        _, fixes_applied = AutoFixService.apply_fixes_and_save(
            dataset_path=original_path,
            binary_issues=binary_issues,
            approved_variables=payload.variables,
            output_path=corrected_path
        )
        
        # Save Fix Audit Log in DB
        fix_log = FixAuditLog(
            validation_id=payload.report_id,
            original_file=original_filename,
            corrected_file=corrected_filename,
            fixes_applied_json=fixes_applied
        )
        db.add(fix_log)
        
        # Update AuditLog summary_data to include corrected dataset reference and fixes log
        summary = dict(audit.summary_data) if audit.summary_data else {}
        summary["corrected_file"] = corrected_filename
        summary["corrected_url"] = f"/api/v1/reports/download/{corrected_filename}"
        summary["fixes_applied"] = fixes_applied
        audit.summary_data = summary
        
        # Also update the report JSON file to include the audit log
        report_data["fix_audit"] = {
            "original_file": original_filename,
            "corrected_file": corrected_filename,
            "corrected_url": f"/api/v1/reports/download/{corrected_filename}",
            "fixes_applied": fixes_applied,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
            
        db.commit()
        
        return {
            "message": "Auto-fixes applied successfully.",
            "original_file": original_filename,
            "corrected_file": corrected_filename,
            "download_url": f"/api/v1/reports/download/{corrected_filename}",
            "fixes_applied": fixes_applied
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply auto-fixes: {str(e)}"
        )

# -------------------------------------------------------------
# AUDIT LOGS & REPORTS ROUTES
# -------------------------------------------------------------
@app.get("/api/v1/validation-history")
def get_validation_history(db: Session = Depends(get_db)):
    """
    Returns the list of all past validation audit logs.
    """
    logs = db.query(AuditLog).order_by(AuditLog.validation_timestamp.desc()).all()
    return logs

@app.get("/api/v1/report/{id}")
def get_report_by_id(id: int, db: Session = Depends(get_db)):
    """
    Retrieves detailed validation report results from JSON file path saved in audit.
    """
    audit = db.query(AuditLog).filter(AuditLog.id == id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit log not found")
        
    # JSON report path in settings.REPORT_DIR
    if audit.report_json_path:
        filename = os.path.basename(audit.report_json_path)
        json_path = os.path.join(settings.REPORT_DIR, filename)
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
                
    raise HTTPException(status_code=404, detail="Report detail file not found")

@app.get("/api/v1/reports/download/{filename}")
def download_report(filename: str):
    """
    Downloads generated XLSX/PDF/JSON reports.
    """
    file_path = os.path.join(settings.REPORT_DIR, filename)

    # Keep legacy reports readable: regenerate PDF/XLSX from JSON using latest formatter.
    if filename.endswith(".pdf") or filename.endswith(".xlsx"):
        base_name, _ = os.path.splitext(filename)
        json_path = os.path.join(settings.REPORT_DIR, f"{base_name}.json")
        if os.path.exists(json_path):
            try:
                from backend.app.reports.excel_gen import ExcelReportGenerator
                from backend.app.reports.pdf_gen import PDFReportGenerator

                with open(json_path, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                if filename.endswith(".pdf"):
                    PDFReportGenerator.generate_report(report_data, file_path)
                else:
                    ExcelReportGenerator.generate_report(report_data, file_path)
            except Exception:
                # Fall back to existing file if regeneration fails.
                pass

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found")
        
    media_type = "application/octet-stream"
    if filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif filename.endswith(".json"):
        media_type = "application/json"
        
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=filename,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

# -------------------------------------------------------------
# PROJECT PROFILE ENDPOINTS
# -------------------------------------------------------------
@app.post("/api/v1/project-profile", response_model=ProjectProfileResponse)
def create_project_profile(profile: ProjectProfileCreate, db: Session = Depends(get_db)):
    """
    Creates a new reusable validation project profile.
    """
    db_profile = db.query(ProjectProfile).filter(ProjectProfile.name == profile.name).first()
    if db_profile:
        raise HTTPException(status_code=400, detail="Profile with this name already exists")
        
    new_profile = ProjectProfile(
        name=profile.name,
        description=profile.description,
        config=profile.config.model_dump()
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return new_profile

@app.post("/api/v1/project-profile/upload-spec", response_model=ProjectProfileResponse)
async def create_profile_from_spec(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    spec: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Creates a new project profile by parsing an uploaded specification template file.
    """
    db_profile = db.query(ProjectProfile).filter(ProjectProfile.name == name).first()
    if db_profile:
        raise HTTPException(status_code=400, detail="Profile with this name already exists")

    # save spec file to uploads temporarily
    spec_path = os.path.join(settings.UPLOAD_DIR, spec.filename)
    with open(spec_path, "wb") as buffer:
        shutil.copyfileobj(spec.file, buffer)

    try:
        # parse spec sheet
        config_data = DataParser.parse_specification_sheet(spec_path)
        
        new_profile = ProjectProfile(
            name=name,
            description=description,
            config=config_data
        )
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        return new_profile
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse spec sheet: {str(e)}"
        )
    finally:
        # delete temporary spec
        if os.path.exists(spec_path):
            try:
                os.remove(spec_path)
            except:
                pass

@app.get("/api/v1/project-profile", response_model=List[ProjectProfileResponse])
def get_project_profiles(db: Session = Depends(get_db)):
    """
    Lists all reusable project profiles.
    """
    return db.query(ProjectProfile).all()

@app.delete("/api/v1/project-profile/{id}")
def delete_project_profile(id: int, db: Session = Depends(get_db)):
    """
    Deletes a project profile.
    """
    profile = db.query(ProjectProfile).filter(ProjectProfile.id == id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Project profile not found")
        
    db.delete(profile)
    db.commit()
    return {"message": "Project profile deleted successfully"}
