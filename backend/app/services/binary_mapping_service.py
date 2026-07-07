import pandas as pd
from typing import Dict, Any, Optional, Tuple

class BinaryMappingService:
    @staticmethod
    def analyze_binary_variable(series: pd.Series) -> Dict[str, Any]:
        """
        Analyzes a series to determine its binary coding pattern.
        Returns:
            Dict: status (PASS/WARNING/FAIL), detected_coding, suggested_fix, confidence_pct, reason
        """
        # Drop missing values
        non_null = series.dropna()
        
        # If string, strip whitespaces
        if pd.api.types.is_string_dtype(non_null):
            non_null = non_null.astype(str).str.strip()
            
        unique_vals = list(non_null.unique())
        
        # Exclude empty values if they converted to empty string
        unique_vals = [v for v in unique_vals if str(v).strip() != ""]
        
        count = len(unique_vals)
        
        if count == 0:
            return {
                "status": "PASS", # Empty columns are caught by Empty Variable Detection
                "detected_coding": "Empty",
                "suggested_fix": None,
                "confidence_pct": 100.0,
                "reason": "Variable contains no valid data."
            }
            
        if count > 2:
            val_strs = ", ".join([str(v) for v in unique_vals[:5]])
            if len(unique_vals) > 5:
                val_strs += ", ..."
            return {
                "status": "FAIL",
                "detected_coding": val_strs,
                "suggested_fix": None,
                "confidence_pct": 0.0,
                "reason": f"More than two valid states detected ({count} states: [{val_strs}])."
            }
            
        if count == 1:
            val = unique_vals[0]
            val_str = str(val).lower().strip()
            # If it's single value, check if it's part of binary
            if val_str in ["0", "0.0"]:
                return {"status": "PASS", "detected_coding": "0", "suggested_fix": None, "confidence_pct": 100.0, "reason": "Single value of 0."}
            elif val_str in ["1", "1.0"]:
                return {"status": "PASS", "detected_coding": "1", "suggested_fix": None, "confidence_pct": 100.0, "reason": "Single value of 1."}
            elif val_str in ["2", "2.0"]:
                return {"status": "WARNING", "detected_coding": "2", "suggested_fix": "2 -> 1", "confidence_pct": 100.0, "reason": "Single value of 2, likely part of 1/2 coding."}
            elif val_str in ["yes", "y", "true", "t"]:
                return {"status": "WARNING", "detected_coding": str(val), "suggested_fix": f"{val} -> 1", "confidence_pct": 100.0, "reason": f"Single value of '{val}', likely part of binary coding."}
            elif val_str in ["no", "n", "false", "f"]:
                return {"status": "WARNING", "detected_coding": str(val), "suggested_fix": f"{val} -> 0", "confidence_pct": 100.0, "reason": f"Single value of '{val}', likely part of binary coding."}
            else:
                return {
                    "status": "FAIL",
                    "detected_coding": str(val),
                    "suggested_fix": None,
                    "confidence_pct": 0.0,
                    "reason": f"Single value of '{val}' is not a recognized binary state."
                }
        
        # Exactly two unique values
        val1, val2 = unique_vals[0], unique_vals[1]
        
        # Core checks
        # Helper to standardize keys to standard types
        def standardize_val(v) -> str:
            # Convert float to int string if applicable (e.g. 1.0 -> "1")
            try:
                f_val = float(v)
                if f_val.is_integer():
                    return str(int(f_val))
                return str(f_val)
            except ValueError:
                return str(v).strip()
                
        s1 = standardize_val(val1)
        s2 = standardize_val(val2)
        s_set = {s1, s2}
        
        # Pattern 1: 0 / 1
        if s_set == {"0", "1"}:
            return {
                "status": "PASS",
                "detected_coding": "0, 1",
                "suggested_fix": None,
                "confidence_pct": 100.0,
                "reason": "Variable is correctly coded as 0 (No) / 1 (Yes)."
            }
            
        # Pattern 2: 1 / 2
        if s_set == {"1", "2"}:
            # Find which is 1 and which is 2 to build proper mapping
            zero_src = "1" if s1 == "1" else "2"
            one_src = "2" if s1 == "1" else "1"
            return {
                "status": "WARNING",
                "detected_coding": "1, 2",
                "suggested_fix": f"{zero_src} -> 0; {one_src} -> 1",
                "confidence_pct": 100.0,
                "reason": "Coded as 1/2 instead of 0/1. Auto-fix map is available."
            }
            
        # Pattern 3: 2 / 4
        if s_set == {"2", "4"}:
            zero_src = "2" if s1 == "2" else "4"
            one_src = "4" if s1 == "2" else "2"
            return {
                "status": "WARNING",
                "detected_coding": "2, 4",
                "suggested_fix": f"{zero_src} -> 0; {one_src} -> 1",
                "confidence_pct": 100.0,
                "reason": "Coded as 2/4 instead of 0/1. Auto-fix map is available."
            }
            
        # Pattern 4 & 5: Y / N or Yes / No (Case Insensitive)
        s_set_lower = {s.lower() for s in s_set}
        if s_set_lower == {"y", "n"}:
            yes_val = val1 if s1.lower() == "y" else val2
            no_val = val2 if s1.lower() == "y" else val1
            return {
                "status": "WARNING",
                "detected_coding": "Y / N",
                "suggested_fix": f"{yes_val} -> 1; {no_val} -> 0",
                "confidence_pct": 100.0,
                "reason": "Coded as Y/N text instead of 0/1. Auto-fix map is available."
            }
            
        if s_set_lower == {"yes", "no"}:
            yes_val = val1 if s1.lower() == "yes" else val2
            no_val = val2 if s1.lower() == "yes" else val1
            return {
                "status": "WARNING",
                "detected_coding": "Yes / No",
                "suggested_fix": f"{yes_val} -> 1; {no_val} -> 0",
                "confidence_pct": 100.0,
                "reason": "Coded as Yes/No text instead of 0/1. Auto-fix map is available."
            }
            
        # Pattern 6: True / False (Boolean or Text)
        if s_set_lower == {"true", "false"}:
            true_val = val1 if s1.lower() == "true" else val2
            false_val = val2 if s1.lower() == "true" else val1
            return {
                "status": "WARNING",
                "detected_coding": "True / False",
                "suggested_fix": f"{true_val} -> 1; {false_val} -> 0",
                "confidence_pct": 100.0,
                "reason": "Coded as True/False instead of 0/1. Auto-fix map is available."
            }
            
        # Pattern 7: T / F
        if s_set_lower == {"t", "f"}:
            true_val = val1 if s1.lower() == "t" else val2
            false_val = val2 if s1.lower() == "t" else val1
            return {
                "status": "WARNING",
                "detected_coding": "T / F",
                "suggested_fix": f"{true_val} -> 1; {false_val} -> 0",
                "confidence_pct": 100.0,
                "reason": "Coded as T/F text instead of 0/1. Auto-fix map is available."
            }
            
        # Fallback: Can we guess which maps to 1 and which to 0?
        # Check if one of them is in [1, "1", "yes", "y", "true", "t"] and the other in [0, "0", "no", "n", "false", "f"]
        yes_candidates = {"1", "yes", "y", "true", "t", "agree", "correct", "pass"}
        no_candidates = {"0", "no", "n", "false", "f", "disagree", "incorrect", "fail"}
        
        s1_lower = s1.lower()
        s2_lower = s2.lower()
        
        is_s1_yes = s1_lower in yes_candidates
        is_s2_yes = s2_lower in yes_candidates
        is_s1_no = s1_lower in no_candidates
        is_s2_no = s2_lower in no_candidates
        
        if (is_s1_yes and is_s2_no) or (is_s2_yes and is_s1_no):
            yes_val = val1 if is_s1_yes else val2
            no_val = val2 if is_s1_yes else val1
            return {
                "status": "WARNING",
                "detected_coding": f"{s1}, {s2}",
                "suggested_fix": f"{yes_val} -> 1; {no_val} -> 0",
                "confidence_pct": 90.0,
                "reason": f"Likely binary coding. Mapped '{yes_val}' as Yes (1) and '{no_val}' as No (0)."
            }
            
        # Random/unresolvable
        return {
            "status": "FAIL",
            "detected_coding": f"{val1}, {val2}",
            "suggested_fix": None,
            "confidence_pct": 0.0,
            "reason": f"Cannot confidently map values [{val1}, {val2}] to 0 (No) / 1 (Yes)."
        }
