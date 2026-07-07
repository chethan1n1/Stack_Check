import os
import json
import datetime
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from backend.app.config import settings
from backend.app.parsers.data_parser import DataParser
from backend.app.validators.profiling_validator import ProfilingValidator
from backend.app.validators.spss_metadata_validator import SPSSMetadataValidator
from backend.app.validators.master_val import MasterVariableValidator
from backend.app.validators.brand_val import BrandVariableValidator
from backend.app.validators.type_val import DataTypeValidator
from backend.app.validators.content_validators import ContentValidators
from backend.app.validators.completeness_validator import CompletenessValidator
from backend.app.validators.quality_score import QualityScoreEngine
from backend.app.services.binary_mapping_service import BinaryMappingService
from backend.app.reports.excel_gen import ExcelReportGenerator
from backend.app.reports.pdf_gen import PDFReportGenerator

class ValidationService:
    @staticmethod
    def run_validation(
        dataset_path: str,
        profile_config: Optional[Dict[str, Any]] = None,
        spec_path: Optional[str] = None,
        mapping_review: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Orchestrates the entire DP Stacked Dataset validation flow.
        """
        # 1. Parse reference specification sheet if uploaded directly
        if spec_path:
            profile_config = DataParser.parse_specification_sheet(spec_path)
        elif not profile_config:
            # Create a default empty profile configuration if none is provided
            profile_config = {"variables": []}
            
        # 2. Parse the Dataset
        df, dataset_metadata = DataParser.parse_dataset(dataset_path)
        
        # Calculate file size
        file_size_mb = os.path.getsize(dataset_path) / (1024 * 1024)
        
        # 3. Run Profiling Validator
        profiler = ProfilingValidator(df, dataset_metadata, profile_config)
        profiling_res = profiler.validate()
        
        # Extract inferred or specified brand and respondent ID columns
        brand_col = profiling_res["potential_brand_variable"]
        resp_id_col = profiling_res["potential_respondent_id"]
        
        # Update metadata schema output
        metadata_summary = {
            "filename": os.path.basename(dataset_path),
            "file_size_mb": round(file_size_mb, 2),
            "file_type": dataset_metadata.get("file_type", "SAV"),
            "rows": len(df),
            "columns": len(df.columns)
        }
        
        # 4. Run SPSS Metadata Validation
        metadata_validator = SPSSMetadataValidator(df, dataset_metadata, profile_config)
        metadata_val_res = metadata_validator.validate()
        
        # 5. Run Master Variable Validation (Checking presence)
        master_validator = MasterVariableValidator(df, dataset_metadata, profile_config)
        master_val_res = master_validator.validate()
        
        # 6. Run Brand Variable Validation (stacked specific checks)
        brand_validator = BrandVariableValidator(df, dataset_metadata, profile_config)
        brand_val_res = brand_validator.validate()
        
        # If brand column found, update
        if brand_val_res.get("exists") and brand_val_res.get("variable"):
            brand_col = brand_val_res["variable"]
            
        # 7. Run Intelligent Binary Validation
        # Locate variables that need binary checks from spec config
        binary_variables_to_check = []
        for var in profile_config.get("variables", []):
            if var.get("is_binary", False) or var.get("category") in ["CEP", "Imagery", "Dependent"]:
                binary_variables_to_check.append(var["name"])
                
        # If no config variables exist, check all columns having 2 unique values
        if not binary_variables_to_check:
            for col in df.columns:
                non_null = df[col].dropna()
                if len(non_null) > 0 and len(non_null.unique()) <= 2:
                    binary_variables_to_check.append(col)
                    
        binary_issues = []
        binary_pass = 0
        binary_warning = 0
        binary_fail = 0
        auto_fix_opps = 0
        
        for col in binary_variables_to_check:
            if col in df.columns:
                analysis = BinaryMappingService.analyze_binary_variable(df[col])
                status = analysis["status"]
                
                if status == "PASS":
                    binary_pass += 1
                elif status == "WARNING":
                    binary_warning += 1
                    auto_fix_opps += 1
                    binary_issues.append({
                        "variable": col,
                        "expected_coding": "0, 1",
                        "detected_coding": analysis["detected_coding"],
                        "severity": "WARNING",
                        "suggested_fix": analysis["suggested_fix"],
                        "confidence_pct": analysis["confidence_pct"],
                        "reason": analysis["reason"]
                    })
                else:
                    binary_fail += 1
                    binary_issues.append({
                        "variable": col,
                        "expected_coding": "0, 1",
                        "detected_coding": analysis["detected_coding"],
                        "severity": "FAIL",
                        "suggested_fix": None,
                        "confidence_pct": 0.0,
                        "reason": analysis["reason"]
                    })
                    
        # Calculate estimated impact for warnings
        from backend.app.services.auto_fix_service import AutoFixService
        try:
            impacts = AutoFixService.get_fixes_impact(dataset_path, binary_issues)
            for issue in binary_issues:
                col = issue.get("variable")
                if col in impacts:
                    issue["impact_data"] = impacts[col]
        except Exception:
            pass

        binary_summary = {
            "pass_count": binary_pass,
            "warning_count": binary_warning,
            "fail_count": binary_fail,
            "auto_fix_opportunities": auto_fix_opps,
            "issues": binary_issues
        }

        # 8. Run Common Missing Respondent Validation
        completeness_validator = CompletenessValidator(
            df,
            dataset_metadata,
            profile_config,
            respondent_id_col=resp_id_col,
            brand_col=brand_col,
        )
        completeness_res = completeness_validator.validate()
        
        # 9. Run Null Analysis
        null_analysis_res = ContentValidators.run_null_analysis(df)
        
        # 10. Run Duplicate Analysis
        duplicate_analysis_res = ContentValidators.run_duplicate_analysis(df, resp_id_col, brand_col)
        
        # 11. Run Empty Variables Detection
        empty_variables_res = ContentValidators.run_empty_variable_detection(df)
        
        # 12. Run Data Type Validation
        datatype_validator = DataTypeValidator(df, dataset_metadata, profile_config)
        datatype_val_res = datatype_validator.validate()
        
        # 13. Calculate Quality Score
        quality_score_res = QualityScoreEngine.calculate_score(
            master_val_res,
            binary_summary,
            metadata_val_res,
            duplicate_analysis_res,
            datatype_val_res,
            completeness_res,
        )
        
        # Determine overall Pass/Fail Status
        final_status = "PASS"
        if quality_score_res["status"] == "Failed" or master_val_res["status"] == "FAIL":
            final_status = "FAIL"
        elif completeness_res.get("status") == "FAIL":
            final_status = "FAIL"
        elif (
            quality_score_res["status"] == "Warning" or 
            binary_summary["warning_count"] > 0 or
            completeness_res.get("status") == "WARNING" or
            any(issue.get("status") == "WARNING" for issue in master_val_res.get("issues", []))
        ):
            final_status = "WARNING"
            
        # Assemble final results dict
        results = {
            "metadata": metadata_summary,
            "profiling": profiling_res,
            "metadata_validation": metadata_val_res,
            "master_validation": master_val_res,
            "binary_validation": binary_summary,
            "completeness_validation": completeness_res,
            "null_analysis": null_analysis_res,
            "duplicate_analysis": duplicate_analysis_res,
            "empty_variables": empty_variables_res,
            "datatype_validation": datatype_val_res,
            "quality_score": quality_score_res,
            "final_status": final_status,
            "profile_config": profile_config,
            "mapping_review": mapping_review or {},
            "audit_metadata": {
                "mapping_review_included": bool(mapping_review),
                "mapping_summary": (mapping_review or {}).get("summary", {}),
            },
        }
        
        # 14. Report Filename Generation
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_base_name = f"Validation_Report_{timestamp}"
        
        xlsx_report_path = os.path.join(settings.REPORT_DIR, f"{report_base_name}.xlsx")
        pdf_report_path = os.path.join(settings.REPORT_DIR, f"{report_base_name}.pdf")
        json_report_path = os.path.join(settings.REPORT_DIR, f"{report_base_name}.json")
        
        # Generate Excel and PDF
        ExcelReportGenerator.generate_report(results, xlsx_report_path)
        PDFReportGenerator.generate_report(results, pdf_report_path)
        
        # Generate JSON Report
        with open(json_report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
            
        # Add relative URL pathways
        results["report_xlsx_url"] = f"/api/v1/reports/download/{os.path.basename(xlsx_report_path)}"
        results["report_pdf_url"] = f"/api/v1/reports/download/{os.path.basename(pdf_report_path)}"
        results["report_json_url"] = f"/api/v1/reports/download/{os.path.basename(json_report_path)}"
        
        return results
