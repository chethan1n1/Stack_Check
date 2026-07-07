import pandas as pd
import numpy as np
from typing import Dict, Any
from backend.app.validators.base import BaseValidator

class ProfilingValidator(BaseValidator):
    def validate(self) -> Dict[str, Any]:
        """
        Profiles the dataset structure and infers key variables.
        """
        df = self.df
        cols = df.columns
        
        numeric_count = 0
        string_count = 0
        binary_count = 0
        date_count = 0
        
        # Analyze each column
        for col in cols:
            series = df[col]
            # Drop null values to check content type
            non_null = series.dropna()
            
            # Check date types
            if pd.api.types.is_datetime64_any_dtype(series):
                date_count += 1
            # Check numeric types
            elif pd.api.types.is_numeric_dtype(series):
                numeric_count += 1
                # If numeric, is it binary?
                unique_vals = non_null.unique()
                if len(unique_vals) <= 2:
                    binary_count += 1
            # Check object/string types
            else:
                string_count += 1
                unique_vals = non_null.unique()
                if len(unique_vals) <= 2:
                    binary_count += 1

        # Infer potential brand variable
        potential_brand = None
        brand_terms = ["brand", "brnd", "brand_id", "brand_name", "brand_code", "brd"]
        for col in cols:
            col_lower = col.lower()
            if any(term in col_lower for term in brand_terms):
                potential_brand = col
                break
        
        # If no brand term matches, look for columns with value labels containing "brand"
        if not potential_brand and "value_labels" in self.metadata:
            for col, labels in self.metadata["value_labels"].items():
                labels_str = " ".join(labels.values()).lower()
                if any(term in labels_str for term in ["brand", "beverage", "chocolate", "product"]):
                    potential_brand = col
                    break
        
        # Infer potential respondent ID
        potential_id = None
        id_terms = ["resp_id", "respid", "respondent", "uid", "uuid", "record_id", "respondent_id", "caseid", "case_id", "id", "pid"]
        
        # Check by name first
        for col in cols:
            col_lower = col.lower()
            # To avoid capturing 'brand_id' as respondent ID
            if "brand" in col_lower:
                continue
            if col_lower in id_terms:
                potential_id = col
                break
        
        # If still not found, check unique numeric variables that could act as respondent ID
        if not potential_id:
            best_uniqueness = 0.0
            candidate_id = None
            for col in cols:
                # Needs to be unique integer
                if pd.api.types.is_integer_dtype(df[col]) or pd.api.types.is_numeric_dtype(df[col]):
                    non_null = df[col].dropna()
                    if len(non_null) > 0:
                        uniqueness = len(non_null.unique()) / len(non_null)
                        if uniqueness == 1.0:
                            candidate_id = col
                            break
            potential_id = candidate_id

        return {
            "rows": len(df),
            "columns": len(cols),
            "numeric_count": numeric_count,
            "string_count": string_count,
            "binary_count": binary_count,
            "date_count": date_count,
            "potential_brand_variable": potential_brand,
            "potential_respondent_id": potential_id
        }
