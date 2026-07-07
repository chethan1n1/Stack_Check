import os
import re
import pandas as pd
import numpy as np
try:
    import pyreadstat
except ImportError:
    pyreadstat = None
from typing import Tuple, Dict, Any, Optional

def detect_csv_encoding(file_path: str) -> str:
    """Attempts to detect CSV encoding. Fallbacks to utf-8 or latin-1."""
    for encoding in ["utf-8", "latin-1", "cp1252", "utf-16"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                f.read(1024)
            return encoding
        except Exception:
            continue
    return "utf-8"

class DataParser:
    NORMALIZED_LABEL_OVERRIDES: dict[str, str] = {
        "custom quesiotn ceps": "Custom Question CEPs",
        "custom question ceps": "Custom Question CEPs",
        "spontaneous awareness": "Spontaneous Awareness",
        "total awareness variable": "Total Awareness Variable",
        "brand variable": "Brand Variable",
        "category entry points": "Category Entry Points",
        "imagery grid": "Imagery Grid",
        "time period": "Time Period",
        "respondent serial": "Respondent Serial",
    }

    @staticmethod
    def _cleanup_common_typos(text: str) -> str:
        fixed = text
        typo_pairs = [
            ("quesiotn", "question"),
            ("questoin", "question"),
            ("anaysis", "analysis"),
            ("fole", "file"),
            ("presentor", "present or"),
        ]
        for wrong, right in typo_pairs:
            fixed = re.sub(rf"\b{re.escape(wrong)}\b", right, fixed, flags=re.IGNORECASE)
        return fixed

    @staticmethod
    def _to_title_case_preserving_tokens(text: str) -> str:
        # Preserve technical tokens/abbreviations like FAM_TRIED, UNIQUE_DA, CEP, MFI.
        tokens = text.split()
        out: list[str] = []
        for tok in tokens:
            if re.search(r"[A-Z]{2,}|_|\d", tok):
                out.append(tok)
            else:
                out.append(tok.capitalize())
        return " ".join(out)

    @staticmethod
    def _standardize_candidate_label(text: str) -> str:
        cleaned = DataParser._cleanup_common_typos(text).strip()
        key = re.sub(r"\s+", " ", cleaned.lower())
        if key in DataParser.NORMALIZED_LABEL_OVERRIDES:
            return DataParser.NORMALIZED_LABEL_OVERRIDES[key]

        # General normalization fallback.
        cleaned = re.sub(r"\s+", " ", cleaned)
        return DataParser._to_title_case_preserving_tokens(cleaned)

    @staticmethod
    def _normalize_form_candidate(candidate: str) -> str:
        text = candidate.strip()
        if not text:
            return ""

        # Remove leading bullets and surrounding brackets.
        text = re.sub(r"^[\-\*\u2022\s]+", "", text)
        if text.startswith("(") and text.endswith(")"):
            text = text[1:-1].strip()

        lower_text = text.lower()
        if lower_text.startswith("please ") or lower_text.startswith("create "):
            return ""

        # Keep the primary phrase before explanatory dashes.
        for sep in [" – ", " — ", " - "]:
            if sep in text:
                text = text.split(sep, 1)[0].strip()

        # For entries like "FAM_TRIED: Brands Tried at Familiarity" keep code/module key.
        if ":" in text:
            prefix = text.split(":", 1)[0].strip()
            if prefix:
                text = prefix

        # Remove remaining short parenthetical notes.
        text = re.sub(r"\s*\(if available\)\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip()

        # Drop long instructional sentences if any still remain.
        if len(text) > 80:
            return ""

        return DataParser._standardize_candidate_label(text)

    @staticmethod
    def _parse_form_like_spec(df: pd.DataFrame) -> list[dict[str, Any]]:
        """
        Parses DP request form-like templates where the sheet is not a structured
        variable table and contains labels such as 'Client:' or 'Date Submitted:'.
        """
        variables: list[dict[str, Any]] = []
        seen: set[str] = set()

        skip_terms = {
            "dp data specification",
            "contacts",
            "client",
            "deadlines",
            "data",
            "general information",
            "questions",
            "reference",
            "other",
        }

        for _, row in df.iterrows():
            row_values = [str(v).strip() for v in row.tolist() if pd.notna(v) and str(v).strip()]
            if not row_values:
                continue

            # The primary label in this template is usually the first non-empty cell.
            label = row_values[0]
            label_norm = label.lower().strip().rstrip(":")

            # Ignore obvious section headers and form prompts.
            if label_norm in skip_terms or label.endswith(":"):
                continue

            # Handle comma-separated variable lists, e.g. "Respondent Serial, yyyymmdd, weekno".
            candidates = [label]
            if "," in label:
                candidates = [part.strip() for part in label.split(",") if part.strip()]

            for candidate in candidates:
                normalized = DataParser._normalize_form_candidate(candidate)
                candidate_norm = normalized.lower().rstrip(":")
                if not candidate_norm or candidate_norm in skip_terms:
                    continue
                if normalized.endswith(":"):
                    continue

                if normalized not in seen:
                    seen.add(normalized)
                    variables.append({
                        "name": normalized,
                        "normalized_label": DataParser._normalize_form_candidate(normalized),
                        "label": None,
                        "category": "Core",
                        "required": True,
                        "data_type": "Numeric",
                        "is_binary": False,
                        "is_analysis_variable": False,
                        "expected_values": None,
                        "value_labels": None,
                    })

        return variables

    @staticmethod
    def parse_dataset(file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Parses a dataset (SAV, XLSX, XLS, CSV) and extracts data and metadata.
        Returns:
            DataFrame: Pandas dataframe of the dataset.
            Dict[str, Any]: Dictionary containing metadata of columns, labels, value labels, types.
        """
        ext = os.path.splitext(file_path)[1].lower()
        df = pd.DataFrame()
        meta_dict = {
            "variable_names": [],
            "variable_labels": {},
            "value_labels": {},
            "variable_types": {},
            "column_candidates": [],
            "missing_ranges": {},
            "file_type": ext.replace(".", "").upper()
        }
        
        if ext == ".sav":
            if pyreadstat is None:
                raise ImportError("The 'pyreadstat' library is not installed in the local Python environment. SPSS (.sav) files cannot be parsed. Please run 'pip install pyreadstat' to parse SPSS files.")
            df, meta = pyreadstat.read_sav(file_path)
            meta_dict["variable_names"] = list(meta.column_names)
            # Match variable name to its label
            meta_dict["variable_labels"] = {
                name: label for name, label in zip(meta.column_names, meta.column_labels) if label
            }
            # Extract value labels mapping
            # pyreadstat stores value labels in variable_value_labels or value_labels
            if hasattr(meta, "variable_value_labels") and meta.variable_value_labels:
                # Value labels are stored as {var_name: {value: label}}
                # Convert float keys to string for JSON compatibility
                meta_dict["value_labels"] = {
                    var: {str(k): str(v) for k, v in labels.items()}
                    for var, labels in meta.variable_value_labels.items()
                }
            
            # Types
            if hasattr(meta, "readstat_variable_types"):
                meta_dict["variable_types"] = meta.readstat_variable_types
            else:
                for col in df.columns:
                    meta_dict["variable_types"][col] = str(df[col].dtype)
            
            # Missing Value Rules
            if hasattr(meta, "missing_user_values") and meta.missing_user_values:
                meta_dict["missing_ranges"] = {
                    var: list(vals) for var, vals in meta.missing_user_values.items() if vals
                }
                
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
            meta_dict["variable_names"] = list(df.columns)
            # Create default metadata for Excel
            for col in df.columns:
                meta_dict["variable_types"][col] = str(df[col].dtype)
                
        elif ext == ".csv":
            encoding = detect_csv_encoding(file_path)
            df = pd.read_csv(file_path, encoding=encoding, low_memory=False)
            meta_dict["variable_names"] = list(df.columns)
            # Create default metadata for CSV
            for col in df.columns:
                meta_dict["variable_types"][col] = str(df[col].dtype)
        else:
            raise ValueError(f"Unsupported dataset format: {ext}")

        # Standardized candidate list for mapping review with rough type hints.
        meta_dict["column_candidates"] = [
            {
                "name": str(col),
                "type_hint": str(df[col].dtype) if col in df.columns else str(meta_dict["variable_types"].get(col, "Unknown")),
            }
            for col in df.columns
        ]
            
        return df, meta_dict

    @staticmethod
    def parse_specification_sheet(file_path: str) -> Dict[str, Any]:
        """
        Parses a DP Specification sheet (XLSX, CSV) and standardizes it.
        Flexible column matching is performed.
        Returns:
            Dict[str, Any]: ProfileConfig structure containing the parsed variables.
        """
        ext = os.path.splitext(file_path)[1].lower()
        module_mappings = []
        if ext in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
            try:
                with pd.ExcelFile(file_path) as xls:
                    if "ModuleMappings" in xls.sheet_names:
                        mm_df = pd.read_excel(xls, "ModuleMappings")
                        raw_mm_cols = {str(col).lower().replace(" ", "").replace("_", ""): col for col in mm_df.columns}
                        bm_col = raw_mm_cols.get("businessmodule", raw_mm_cols.get("module", None))
                        vp_col = raw_mm_cols.get("variablepattern", raw_mm_cols.get("pattern", None))
                        req_col = raw_mm_cols.get("required", raw_mm_cols.get("mandatory", None))
                        desc_col = raw_mm_cols.get("description", None)
                        
                        if not bm_col and len(mm_df.columns) > 0:
                            bm_col = mm_df.columns[0]
                        if not vp_col and len(mm_df.columns) > 1:
                            vp_col = mm_df.columns[1]
                        if not req_col and len(mm_df.columns) > 2:
                            req_col = mm_df.columns[2]
                        if not desc_col and len(mm_df.columns) > 3:
                            desc_col = mm_df.columns[3]
                            
                        if bm_col and vp_col:
                            for _, row in mm_df.iterrows():
                                bm_val = str(row[bm_col]).strip() if pd.notna(row[bm_col]) else ""
                                vp_val = str(row[vp_col]).strip() if pd.notna(row[vp_col]) else ""
                                if not bm_val or bm_val.lower() in ["nan", "null", "none", ""]:
                                    continue
                                    
                                is_req = True
                                if req_col and req_col in row and pd.notna(row[req_col]):
                                    val_str = str(row[req_col]).strip().lower()
                                    if val_str in ["no", "n", "false", "0", "optional"]:
                                        is_req = False
                                        
                                desc_val = ""
                                if desc_col and desc_col in row and pd.notna(row[desc_col]):
                                    desc_val = str(row[desc_col]).strip()
                                    
                                module_mappings.append({
                                    "business_module": bm_val,
                                    "variable_pattern": vp_val,
                                    "required": is_req,
                                    "description": desc_val
                                })
            except Exception:
                pass
        elif ext == ".csv":
            encoding = detect_csv_encoding(file_path)
            df = pd.read_csv(file_path, encoding=encoding)
        else:
            raise ValueError(f"Unsupported specification format: {ext}")
            
        # Clean column names to find matches
        raw_cols = {col.lower().replace(" ", "").replace("_", ""): col for col in df.columns}
        
        # Mappings
        name_col = raw_cols.get("variablename", raw_cols.get("variable", raw_cols.get("name", None)))
        label_col = raw_cols.get("variablelabel", raw_cols.get("label", None))
        cat_col = raw_cols.get("category", raw_cols.get("group", raw_cols.get("type", None)))
        req_col = raw_cols.get("required", raw_cols.get("mandatory", None))
        type_col = raw_cols.get("datatype", raw_cols.get("type", raw_cols.get("expectedtype", None)))
        binary_col = raw_cols.get("isbinary", raw_cols.get("binary", None))
        val_col = raw_cols.get("expectedvalues", raw_cols.get("values", None))
        val_label_col = raw_cols.get("valuelabels", raw_cols.get("valuelabel", None))
        analysis_col = raw_cols.get(
            "analysisvariable",
            raw_cols.get(
                "isanalysisvariable",
                raw_cols.get("analysis", raw_cols.get("foranalysis", raw_cols.get("modelvariable", None)))
            )
        )

        name_col_detected = bool(name_col)
        if not name_col:
            # Fallback to the first column if name column is not identified
            name_col = df.columns[0]

        # Handle form-style DP templates that are not structured variable tables.
        has_structured_columns = any([label_col, cat_col, req_col, type_col, binary_col, val_col, val_label_col])
        if not name_col_detected and not has_structured_columns:
            form_variables = DataParser._parse_form_like_spec(df)
            if form_variables:
                return {"variables": form_variables, "module_mappings": module_mappings}
            
        variables = []
        for _, row in df.iterrows():
            var_name = str(row[name_col]).strip()
            if not var_name or var_name.lower() in ["nan", "null", "none", ""]:
                continue
                
            var_label = str(row[label_col]).strip() if label_col and pd.notna(row[label_col]) else None
            
            # Category
            category = "Core"
            if cat_col and pd.notna(row[cat_col]):
                val = str(row[cat_col]).strip().lower()
                if "core" in val: category = "Core"
                elif "brand" in val: category = "Brand"
                elif "dependent" in val: category = "Dependent"
                elif "cep" in val: category = "CEP"
                elif "imagery" in val: category = "Imagery"
                elif "strategic" in val: category = "Strategic"
                else: category = "Optional"
                
            # Required
            required = True
            if req_col and pd.notna(row[req_col]):
                val = str(row[req_col]).strip().lower()
                if val in ["no", "n", "false", "0", "optional"]:
                    required = False
                    
            # Data Type
            data_type = "Numeric"
            if type_col and pd.notna(row[type_col]):
                val = str(row[type_col]).strip().lower()
                if "int" in val: data_type = "Integer"
                elif "float" in val or "num" in val: data_type = "Numeric"
                elif "str" in val or "char" in val or "text" in val: data_type = "String"
                elif "bool" in val: data_type = "Boolean"
                elif "date" in val: data_type = "Date"
                
            # Is Binary
            is_binary = False
            if binary_col and pd.notna(row[binary_col]):
                val = str(row[binary_col]).strip().lower()
                if val in ["yes", "y", "true", "1", "binary"]:
                    is_binary = True
            elif category in ["CEP", "Imagery"]:
                is_binary = True  # Default to binary for CEP and Imagery
                
            # Expected Values
            expected_values = None
            if val_col and pd.notna(row[val_col]):
                val = str(row[val_col]).strip()
                if val:
                    # e.g., "0;1" or "1;2;3" or "Male;Female"
                    expected_values = [v.strip() for v in val.split(";")]
                    # Convert to numeric if possible
                    for i in range(len(expected_values)):
                        try:
                            # Try parsing as float/int
                            val_f = float(expected_values[i])
                            if val_f.is_integer():
                                expected_values[i] = int(val_f)
                            else:
                                expected_values[i] = val_f
                        except ValueError:
                            pass
            
            # Value Labels
            value_labels = None
            if val_label_col and pd.notna(row[val_label_col]):
                val = str(row[val_label_col]).strip()
                if val:
                    # e.g., "0 = No; 1 = Yes" or "1 = Male; 2 = Female"
                    value_labels = {}
                    parts = val.split(";")
                    for p in parts:
                        if "=" in p:
                            k, v = p.split("=", 1)
                            # Remove floats if integer string representation (e.g. "1.0")
                            k_str = k.strip()
                            try:
                                k_f = float(k_str)
                                if k_f.is_integer():
                                    k_str = str(int(k_f))
                            except ValueError:
                                pass
                            value_labels[k_str] = v.strip()

            # Analysis Variable Flag
            is_analysis_variable = False
            if analysis_col and analysis_col in row and pd.notna(row[analysis_col]):
                val = str(row[analysis_col]).strip().lower()
                if val in ["yes", "y", "true", "1", "analysis", "model", "x"]:
                    is_analysis_variable = True
            
            variables.append({
                "name": var_name,
                "normalized_label": DataParser._normalize_form_candidate(var_name),
                "label": var_label,
                "category": category,
                "required": required,
                "data_type": data_type,
                "is_binary": is_binary,
                "is_analysis_variable": is_analysis_variable,
                "expected_values": expected_values,
                "value_labels": value_labels
            })
            
        return {"variables": variables, "module_mappings": module_mappings}
