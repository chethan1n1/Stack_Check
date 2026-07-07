import pandas as pd
from typing import Dict, Any, List

class ContentValidators:
    @staticmethod
    def run_null_analysis(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates null counts, null %, and blank % for each column.
        Determines color thresholds:
        - Green: 0-5%
        - Yellow: 5-20%
        - Red: 20%+
        """
        variables = []
        green_count = 0
        yellow_count = 0
        red_count = 0
        
        total_rows = len(df)
        
        for col in df.columns:
            series = df[col]
            null_count = series.isna().sum()
            null_pct = (null_count / total_rows) * 100 if total_rows > 0 else 0.0
            
            # Blank check (for strings)
            blank_count = 0
            if pd.api.types.is_string_dtype(series):
                blank_count = (series.astype(str).str.strip() == "").sum()
            blank_pct = (blank_count / total_rows) * 100 if total_rows > 0 else 0.0
            
            # Total empty pct (null + blank)
            empty_pct = null_pct + blank_pct
            
            if empty_pct <= 5.0:
                status = "GREEN"
                green_count += 1
            elif empty_pct <= 20.0:
                status = "YELLOW"
                yellow_count += 1
            else:
                status = "RED"
                red_count += 1
                
            variables.append({
                "variable": col,
                "null_count": int(null_count),
                "null_pct": round(null_pct, 2),
                "blank_pct": round(blank_pct, 2),
                "status": status
            })
            
        return {
            "green_count": green_count,
            "yellow_count": yellow_count,
            "red_count": red_count,
            "variables": variables
        }

    @staticmethod
    def run_duplicate_analysis(df: pd.DataFrame, resp_id_col: str = None, brand_col: str = None) -> Dict[str, Any]:
        """
        Validates duplicate respondent IDs, duplicate full records, and duplicate brand rows.
        """
        total_rows = len(df)
        dup_respondents = 0
        dup_rows = 0
        dup_brand_rows = 0
        
        # 1. Full Row Duplicates
        dup_rows = df.duplicated().sum()
        
        # 2. Duplicate Respondent IDs
        if resp_id_col and resp_id_col in df.columns:
            dup_respondents = df[resp_id_col].duplicated().sum()
            
        # 3. Duplicate Brand Rows (Combination of Respondent ID + Brand Variable)
        if resp_id_col and resp_id_col in df.columns and brand_col and brand_col in df.columns:
            dup_brand_rows = df.duplicated(subset=[resp_id_col, brand_col]).sum()
            
        return {
            "duplicate_respondents_count": int(dup_respondents),
            "duplicate_rows_count": int(dup_rows),
            "duplicate_brand_rows_count": int(dup_brand_rows),
            "respondent_id_col": resp_id_col,
            "brand_col": brand_col
        }

    @staticmethod
    def run_empty_variable_detection(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detects 100% null/blank columns or constant columns (constant value).
        """
        empty_vars = []
        total_rows = len(df)
        
        for col in df.columns:
            series = df[col]
            null_count = series.isna().sum()
            
            # String blank check
            blank_count = 0
            if pd.api.types.is_string_dtype(series):
                blank_count = (series.astype(str).str.strip() == "").sum()
                
            if (null_count + blank_count) == total_rows:
                empty_vars.append({
                    "variable": col,
                    "type": "EMPTY",
                    "constant_value": None
                })
            else:
                # Check constant values
                non_null = series.dropna()
                if pd.api.types.is_string_dtype(non_null):
                    non_null = non_null[non_null.astype(str).str.strip() != ""]
                    
                unique_vals = non_null.unique()
                if len(unique_vals) == 1:
                    empty_vars.append({
                        "variable": col,
                        "type": "CONSTANT",
                        "constant_value": str(unique_vals[0])
                    })
                    
        return empty_vars
