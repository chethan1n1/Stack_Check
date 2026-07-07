import pandas as pd
from typing import Dict, Any, List
from backend.app.validators.base import BaseValidator

class MasterVariableValidator(BaseValidator):
    def validate(self) -> Dict[str, Any]:
        """
        Validates variables in the dataset against the profile specification.
        Checks:
        - Variable Exists
        - Variable Missing (Required Core vs Optional)
        - Unexpected Variables
        - Coverage %
        """
        df = self.df
        config = self.config
        
        import re
        import json
        import os
        from backend.app.config.settings import settings
        from backend.app.config import normalize_module_name

        dataset_vars = list(df.columns)
        dataset_vars_set = set(df.columns)
        
        mappings_path = os.path.join(settings.BASE_DIR, "app", "config", "module_mappings.json")
        if not os.path.exists(mappings_path):
            mappings_path = os.path.join(settings.BASE_DIR, "backend", "app", "config", "module_mappings.json")
            
        raw_module_mappings = {}
        if os.path.exists(mappings_path):
            try:
                with open(mappings_path, "r", encoding="utf-8") as f:
                    raw_module_mappings = json.load(f)
            except Exception:
                pass

        def is_business_module_candidate(module_name: str) -> bool:
            if " " in module_name:
                return True
            known_modules = {
                "consideration", "imagery", "cep", "familiarity", "affinity", 
                "trust", "brandlove", "innovation", "recommendation", 
                "sustainability", "availability", "valueformoney"
            }
            if normalize_module_name(module_name) in known_modules:
                return True
            # Also if it exists in Excel or JSON mappings, it is a business module
            excel_mappings = config.get("module_mappings", []) if config else []
            for mm in excel_mappings:
                if normalize_module_name(mm.get("business_module", "")) == normalize_module_name(module_name):
                    return True
            for j_key in raw_module_mappings:
                if normalize_module_name(j_key) == normalize_module_name(module_name):
                    return True
            return False

        def suggest_pattern_for_module(module_name: str, dataset_v: list) -> Dict[str, Any]:
            parts = [part.strip().upper() for part in re.split(r'[\s_\-]+', module_name) if part.strip()]
            if parts:
                prefix = "_".join(parts)
                suggested = f"{prefix}_.*"
            else:
                suggested = f"{module_name.upper().strip()}_.*"
                
            try:
                pattern_re = re.compile(f"^{suggested}$", re.IGNORECASE)
            except Exception:
                pattern_re = None
                
            matched = []
            if pattern_re:
                for col in dataset_v:
                    if pattern_re.match(col):
                        matched.append(col)
                        
            if matched:
                confidence = 95.0
                status = "Suggested"
            else:
                confidence = 0.0
                status = "UNKNOWN"
                
            return {
                "suggested_pattern": suggested,
                "matched_variables": matched,
                "match_count": len(matched),
                "confidence_pct": confidence,
                "status": status
            }

        # Keep track of which dataset columns were matched to avoid duplicate assignments
        matched_dataset_cols = set()
        
        # Build map of expected variables
        expected_vars = {v["name"]: v for v in config.get("variables", [])} if config else {}
        
        issues = []
        module_resolution_report = []
        unknown_modules_report = []
        module_mapping_summary = [] # for backwards-compatibility / rendering Sheet 7
        
        required_count = 0
        found_count = 0
        missing_count = 0
        unexpected_count = 0
        
        # Check expected variables
        for name, spec in expected_vars.items():
            is_required = spec.get("required", True)
            is_core = spec.get("category", "Core") == "Core"
            
            if is_required:
                required_count += 1
                
            normalized_name = normalize_module_name(name)
            
            # Step 1: Excel Mapping Lookup
            excel_mapping = None
            excel_mappings = config.get("module_mappings", []) if config else []
            if excel_mappings:
                for mm in excel_mappings:
                    if normalize_module_name(mm.get("business_module", "")) == normalized_name:
                        excel_mapping = mm
                        break
                        
            # Step 2: JSON Mapping Lookup (with Aliases support)
            json_mapping = None
            if not excel_mapping:
                for j_key, j_val in raw_module_mappings.items():
                    normalized_key = normalize_module_name(j_key)
                    aliases = []
                    patterns = []
                    if isinstance(j_val, dict):
                        aliases = [normalize_module_name(a) for a in j_val.get("aliases", [])]
                        patterns = j_val.get("patterns", [])
                    else:
                        patterns = j_val
                        
                    if normalized_name == normalized_key or normalized_name in aliases:
                        json_mapping = {
                            "key": j_key,
                            "patterns": patterns
                        }
                        break
                        
            # Determine mapping & run resolution
            matched_cols_for_this_var = []
            source_used = None
            pattern_str = None
            
            if excel_mapping:
                source_used = "Excel Mapping"
                pattern_str = excel_mapping.get("variable_pattern", "")
                patterns = [p.strip() for p in pattern_str.split(",") if p.strip()] if "," in pattern_str else [pattern_str.strip()]
                for p in patterns:
                    try:
                        p_re = re.compile(f"^{p}$", re.IGNORECASE)
                        for col in dataset_vars:
                            if col not in matched_dataset_cols and p_re.match(col):
                                matched_cols_for_this_var.append(col)
                    except Exception:
                        pass
                        
            elif json_mapping:
                source_used = "JSON Mapping"
                patterns = json_mapping["patterns"]
                pattern_str = ", ".join(patterns)
                for p in patterns:
                    try:
                        p_re = re.compile(f"^{p}$", re.IGNORECASE)
                        for col in dataset_vars:
                            if col not in matched_dataset_cols and p_re.match(col):
                                matched_cols_for_this_var.append(col)
                    except Exception:
                        pass
                        
            else:
                # No mapping found, check standard exact/case-insensitive/regex match
                matched_col = None
                if name in dataset_vars_set and name not in matched_dataset_cols:
                    matched_col = name
                else:
                    for col in dataset_vars:
                        if col.lower() == name.lower() and col not in matched_dataset_cols:
                            matched_col = col
                            break
                    if not matched_col:
                        try:
                            p_re = re.compile(rf"^{name}$", re.IGNORECASE)
                            for col in dataset_vars:
                                if col not in matched_dataset_cols and p_re.match(col):
                                    matched_col = col
                                    break
                        except Exception:
                            pass
                            
                if matched_col:
                    matched_cols_for_this_var = [matched_col]
                    source_used = "Standard Match"
                    pattern_str = name
                else:
                    # Decide if we treat as Unknown Module or Standard Missing
                    if is_business_module_candidate(name):
                        # Step 3: Trigger Unknown Module Detection
                        source_used = "Auto Discovery"
                        suggestion = suggest_pattern_for_module(name, dataset_vars)
                        pattern_str = suggestion["suggested_pattern"]
                        matched_cols_for_this_var = []
                    else:
                        source_used = "Standard Match"
                        pattern_str = name
                        matched_cols_for_this_var = []
                    
            # Update validation counts & record issues
            if source_used == "Auto Discovery":
                # Unknown module detection
                unknown_modules_report.append({
                    "business_module": name,
                    "suggested_pattern": pattern_str,
                    "reason": "No mapping found in Excel or module_mappings.json"
                })
                
                module_resolution_report.append({
                    "business_module": name,
                    "normalized_name": normalized_name,
                    "source": source_used,
                    "matched_pattern": pattern_str,
                    "matched_variables": "None",
                    "match_count": 0,
                    "status": "UNKNOWN"
                })
                
                module_mapping_summary.append({
                    "business_module": name,
                    "pattern_used": pattern_str,
                    "matched_variables": "None",
                    "match_count": 0,
                    "status": "UNKNOWN"
                })
                
                # Report as WARNING (Configuration Missing, do not fail validation immediately, avoid score reduction)
                issues.append({
                    "variable": name,
                    "category": spec.get("category", "Core"),
                    "status": "WARNING",
                    "required": is_required,
                    "reason": "Configuration Missing",
                    "details": f"Unknown Module: '{name}' (no mapping found in Excel or module_mappings.json)"
                })
                
            else:
                if matched_cols_for_this_var:
                    found_count += 1
                    for c in matched_cols_for_this_var:
                        matched_dataset_cols.add(c)
                        issues.append({
                            "variable": c,
                            "category": spec.get("category", "Core"),
                            "status": "FOUND",
                            "required": is_required
                        })
                        
                    module_resolution_report.append({
                        "business_module": name,
                        "normalized_name": normalized_name,
                        "source": source_used,
                        "matched_pattern": pattern_str,
                        "matched_variables": ", ".join(matched_cols_for_this_var),
                        "match_count": len(matched_cols_for_this_var),
                        "status": "FOUND"
                    })
                    
                    module_mapping_summary.append({
                        "business_module": name,
                        "pattern_used": pattern_str,
                        "matched_variables": ", ".join(matched_cols_for_this_var),
                        "match_count": len(matched_cols_for_this_var),
                        "status": "FOUND"
                    })
                else:
                    # Missing module mapping but is required/optional
                    missing_count += 1
                    if is_required:
                        status_val = "MISSING"
                        issues.append({
                            "variable": name,
                            "category": spec.get("category", "Core"),
                            "status": status_val,
                            "required": True
                        })
                    else:
                        status_val = "MISSING"
                        issues.append({
                            "variable": name,
                            "category": spec.get("category", "Optional"),
                            "status": status_val,
                            "required": False
                        })
                        
                    module_resolution_report.append({
                        "business_module": name,
                        "normalized_name": normalized_name,
                        "source": source_used,
                        "matched_pattern": pattern_str,
                        "matched_variables": "None",
                        "match_count": 0,
                        "status": "MISSING"
                    })
                    
                    module_mapping_summary.append({
                        "business_module": name,
                        "pattern_used": pattern_str,
                        "matched_variables": "None",
                        "match_count": 0,
                        "status": "MISSING"
                    })
                    
        # Check unexpected variables in dataset
        for col in df.columns:
            if col not in matched_dataset_cols:
                unexpected_count += 1
                issues.append({
                    "variable": col,
                    "category": "Unexpected",
                    "status": "UNEXPECTED",
                    "required": False
                })
                
        coverage_pct = (found_count / len(expected_vars)) * 100 if expected_vars else 100.0
        
        # Check if any required Core variables are missing (Exclude configuration missing warnings)
        has_missing_core = any(
            issue["category"] == "Core" and issue["status"] == "MISSING" and issue["required"]
            for issue in issues
        )
        status = "FAIL" if has_missing_core else "PASS"
        
        return {
            "required_count": required_count,
            "found_count": found_count,
            "missing_count": missing_count,
            "unexpected_count": unexpected_count,
            "coverage_pct": round(coverage_pct, 1),
            "status": status,
            "issues": issues,
            "module_mappings": module_mapping_summary,
            "module_resolution_report": module_resolution_report,
            "unknown_modules_report": unknown_modules_report
        }
