import os
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
try:
    import pyreadstat
except ImportError:
    pyreadstat = None

class AutoFixService:
    @staticmethod
    def get_fixes_impact(dataset_path: str, binary_issues: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Calculates affected row counts, percentages, and impact severities for previewing fixes.
        """
        impacts = {}
        ext = os.path.splitext(dataset_path)[1].lower()
        
        try:
            # Quick read to inspect values (we only need the columns in question)
            cols_to_read = [issue["variable"] for issue in binary_issues if "variable" in issue]
            if not cols_to_read:
                return {}
                
            if ext == ".sav":
                if pyreadstat is None:
                    return {}
                # pyreadstat allows reading specific columns
                df, _ = pyreadstat.read_sav(dataset_path, usecols=cols_to_read)
            elif ext in [".xlsx", ".xls"]:
                # read only the header + columns
                df = pd.read_excel(dataset_path, usecols=cols_to_read)
            elif ext == ".csv":
                from backend.app.parsers.data_parser import detect_csv_encoding
                encoding = detect_csv_encoding(dataset_path)
                df = pd.read_csv(dataset_path, usecols=cols_to_read, encoding=encoding, low_memory=False)
            else:
                return {}
        except Exception:
            # Fallback if selective reading fails (e.g. columns missing)
            return {}

        total_rows = len(df)
        if total_rows == 0:
            return {}

        for issue in binary_issues:
            col = issue.get("variable")
            suggested_fix = issue.get("suggested_fix")
            if not col or col not in df.columns or not suggested_fix:
                continue

            # Parse target source values
            src_values = []
            parts = [p.strip() for p in suggested_fix.split(";")]
            for p in parts:
                if "->" in p:
                    src = p.split("->", 1)[0].strip()
                    src_values.append(src)
                    
            # Count how many rows in the column have values matching the source strings/numbers
            non_null = df[col].dropna()
            affected_rows = 0
            for val in non_null:
                val_str = str(val).strip()
                # Also handle float representation (e.g. 1.0 vs 1)
                try:
                    val_f = float(val)
                    val_is_int = val_f.is_integer()
                except ValueError:
                    val_f = None
                    val_is_int = False

                is_affected = False
                for src in src_values:
                    if val_str == src:
                        is_affected = True
                        break
                    try:
                        src_f = float(src)
                        if val_f == src_f:
                            is_affected = True
                            break
                    except ValueError:
                        pass
                
                if is_affected:
                    affected_rows += 1

            affected_pct = round((affected_rows / total_rows) * 100, 1)
            
            # Severity classification
            if affected_pct > 80:
                severity = "HIGH"
            elif affected_pct > 10:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            impacts[col] = {
                "affected_rows": affected_rows,
                "affected_pct": affected_pct,
                "severity": severity
            }

        return impacts

    @staticmethod
    def apply_fixes_and_save(
        dataset_path: str,
        binary_issues: List[Dict[str, Any]],
        approved_variables: List[str],
        output_path: str
    ) -> Tuple[str, Dict[str, str]]:
        """
        Applies selective recoding transformations and exports the corrected dataset,
        preserving all SPSS variable and value labels.
        Returns:
            str: Path to the generated fixed dataset.
            Dict[str, str]: Log of applied fixes.
        """
        ext = os.path.splitext(dataset_path)[1].lower()
        df = pd.DataFrame()
        pyreadstat_meta = None
        
        if ext == ".sav":
            if pyreadstat is None:
                raise ImportError("pyreadstat is not installed.")
            df, pyreadstat_meta = pyreadstat.read_sav(dataset_path)
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(dataset_path)
        elif ext == ".csv":
            from backend.app.parsers.data_parser import detect_csv_encoding
            encoding = detect_csv_encoding(dataset_path)
            df = pd.read_csv(dataset_path, encoding=encoding, low_memory=False)
        else:
            raise ValueError(f"Unsupported format: {ext}")

        fixes_applied = {}
        updated_value_labels = {}
        
        if pyreadstat_meta and hasattr(pyreadstat_meta, "variable_value_labels"):
            # Deep copy existing labels
            updated_value_labels = {k: dict(v) for k, v in pyreadstat_meta.variable_value_labels.items() if v}

        approved_set = set(approved_variables)
        
        for issue in binary_issues:
            col = issue.get("variable")
            suggested_fix = issue.get("suggested_fix")
            severity = issue.get("severity")
            
            if col not in approved_set or col not in df.columns or not suggested_fix:
                continue

            # Parse suggested fix, e.g. "1 -> 0; 2 -> 1"
            mapping = {}
            parts = [p.strip() for p in suggested_fix.split(";")]
            for p in parts:
                if "->" in p:
                    src, dst = p.split("->", 1)
                    src_str = src.strip()
                    dst_str = dst.strip()
                    
                    try:
                        dst_val = float(dst_str)
                        if dst_val.is_integer():
                            dst_val = int(dst_val)
                    except ValueError:
                        dst_val = dst_str
                        
                    mapping[src_str] = dst_val
                    try:
                        src_f = float(src_str)
                        mapping[src_f] = dst_val
                        if src_f.is_integer():
                            mapping[int(src_f)] = dst_val
                    except ValueError:
                        pass

            # Apply mapping function
            df[col] = df[col].map(lambda val: mapping.get(val, mapping.get(str(val).strip(), val)))
            fixes_applied[col] = suggested_fix

            # SPSS Value Labels alignment
            if pyreadstat_meta:
                # Re-label the recoded states (0=No, 1=Yes etc.)
                orig_labels = updated_value_labels.get(col, {})
                new_labels = {}
                
                # Check for standard mapping from string representation
                for orig_val, label in orig_labels.items():
                    # Translate key based on mapping
                    translated_key = mapping.get(orig_val, mapping.get(str(orig_val).strip(), orig_val))
                    try:
                        translated_key = float(translated_key)
                    except ValueError:
                        pass
                    new_labels[translated_key] = label
                    
                # Ensure we have both 0 and 1 labeled if it is standard binary mapping
                if 0.0 not in new_labels and 0 in new_labels:
                    new_labels[0.0] = new_labels[0]
                if 1.0 not in new_labels and 1 in new_labels:
                    new_labels[1.0] = new_labels[1]
                    
                updated_value_labels[col] = new_labels

        # Write fixed output file
        if ext == ".sav":
            column_labels = pyreadstat_meta.column_labels if hasattr(pyreadstat_meta, "column_labels") else None
            variable_types = pyreadstat_meta.readstat_variable_types if hasattr(pyreadstat_meta, "readstat_variable_types") else None
            
            pyreadstat.write_sav(
                df,
                output_path,
                column_labels=column_labels,
                variable_value_labels=updated_value_labels
            )
        elif ext in [".xlsx", ".xls"]:
            df.to_excel(output_path, index=False)
        elif ext == ".csv":
            df.to_csv(output_path, index=False)
            
        return output_path, fixes_applied
