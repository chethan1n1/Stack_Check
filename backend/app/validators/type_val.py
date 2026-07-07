import pandas as pd
import numpy as np
from typing import Dict, Any, List
from backend.app.validators.base import BaseValidator

class DataTypeValidator(BaseValidator):
    def validate(self) -> List[Dict[str, Any]]:
        """
        Validates column datatypes.
        Checks actual datatype vs expected datatype from config.
        Returns:
            List[Dict]: List of mismatch issues.
        """
        df = self.df
        config = self.config
        
        mismatches = []
        expected_vars = {v["name"]: v for v in config.get("variables", [])}
        
        for col in df.columns:
            if col not in expected_vars:
                continue
                
            spec = expected_vars[col]
            expected_type = spec.get("data_type", "Numeric")
            series = df[col]
            
            # Skip if entirely null
            if series.isna().sum() == len(df):
                continue
                
            # Get actual type
            dtype_str = str(series.dtype)
            
            is_valid = True
            actual_type = "String"
            
            # Identify actual type
            if pd.api.types.is_integer_dtype(series):
                actual_type = "Integer"
            elif pd.api.types.is_numeric_dtype(series):
                # Check if it has float decimals
                non_null = series.dropna()
                # Check if all floats are integers
                is_all_int = all(float(x).is_integer() for x in non_null.values) if len(non_null) > 0 else True
                actual_type = "Integer" if is_all_int else "Float"
            elif pd.api.types.is_datetime64_any_dtype(series):
                actual_type = "Date"
            elif pd.api.types.is_bool_dtype(series):
                actual_type = "Boolean"
            else:
                # String or mixed object
                actual_type = "String"
                # Check if it is parseable to date or float
                non_null = series.dropna().astype(str).str.strip()
                if len(non_null) > 0:
                    # Check if all can parse as floats
                    try:
                        pd.to_numeric(non_null)
                        # All numeric strings, so actual type could be numeric represented as text
                        actual_type = "String (Numeric values)"
                    except ValueError:
                        pass

            # Perform Mismatch Check
            if expected_type == "Integer":
                if actual_type not in ["Integer"]:
                    # If it's Float but contains decimal values, it's a mismatch
                    is_valid = False
            elif expected_type in ["Numeric", "Float"]:
                if actual_type not in ["Integer", "Float", "Numeric"]:
                    # String values in numeric column
                    is_valid = False
            elif expected_type == "String":
                if actual_type in ["Integer", "Float", "Boolean"]:
                    # Numeric column when expected string
                    is_valid = False
            elif expected_type == "Boolean":
                if actual_type not in ["Boolean", "Integer"]:
                    is_valid = False
                else:
                    # If Integer, verify it only contains 0 and 1
                    non_null = series.dropna()
                    unique_vals = set(non_null.unique())
                    if not unique_vals.issubset({0, 1, 0.0, 1.0}):
                        is_valid = False
            elif expected_type == "Date":
                if actual_type != "Date":
                    # Check if it can be parsed as dates
                    non_null = series.dropna()
                    try:
                        pd.to_datetime(non_null)
                    except Exception:
                        is_valid = False

            if not is_valid:
                mismatches.append({
                    "variable": col,
                    "expected_type": expected_type,
                    "actual_type": actual_type,
                    "status": "FAIL"
                })
                
        return mismatches
