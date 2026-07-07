import pandas as pd
from typing import Dict, Any, List
from backend.app.validators.base import BaseValidator

class BrandVariableValidator(BaseValidator):
    def validate(self) -> Dict[str, Any]:
        """
        Validates brand variable.
        Checks:
        - Brand Variable Exists
        - Brand Variable Not Empty
        - Brand Variable Properly Coded (Value Labels present)
        - Brand Distribution
        """
        df = self.df
        config = self.config
        metadata = self.metadata
        
        # 1. Identify Brand Variable
        brand_col = None
        
        # Try to find from profile config
        for var in config.get("variables", []):
            if var.get("category") == "Brand":
                brand_col = var["name"]
                break
                
        # Fallback to metadata / heuristics
        if not brand_col or brand_col not in df.columns:
            brand_terms = ["brand", "brnd", "brand_id", "brand_name", "brand_code", "brd"]
            for col in df.columns:
                if any(term in col.lower() for term in brand_terms):
                    brand_col = col
                    break
        
        # If still not found, check if there's any column that has "brand" value labels
        if not brand_col and "value_labels" in metadata:
            for col, labels in metadata["value_labels"].items():
                labels_str = " ".join(labels.values()).lower()
                if any(term in labels_str for term in ["brand", "beverage", "chocolate", "product"]):
                    brand_col = col
                    break
                    
        if not brand_col or brand_col not in df.columns:
            return {
                "exists": False,
                "variable": None,
                "not_empty": False,
                "properly_coded": False,
                "distribution": {},
                "status": "FAIL",
                "message": "Brand variable not found in dataset."
            }

        # 2. Check if Empty
        series = df[brand_col]
        null_count = series.isna().sum()
        total_rows = len(df)
        null_pct = (null_count / total_rows) * 100 if total_rows > 0 else 100.0
        not_empty = null_pct < 100.0
        
        # 3. Check value labels
        value_labels = metadata.get("value_labels", {}).get(brand_col, {})
        has_labels = len(value_labels) > 0
        
        # 4. Brand Distribution
        non_null = series.dropna()
        distribution = {}
        
        if len(non_null) > 0:
            counts = non_null.value_counts()
            for val, count in counts.items():
                val_str = str(val)
                # If there's a label in pyreadstat, resolve it
                label = value_labels.get(val_str, value_labels.get(str(int(val)) if isinstance(val, (int, float)) and val.is_integer() else val_str, val_str))
                pct = (count / len(non_null)) * 100
                distribution[label] = {
                    "count": int(count),
                    "percentage": round(pct, 2)
                }

        # Overall Status
        # Must exist, not be fully empty, and have labels to PASS
        status = "PASS"
        if null_pct > 10.0:  # If more than 10% are empty, warn/fail
            status = "WARNING"
        if not not_empty:
            status = "FAIL"
            
        return {
            "exists": True,
            "variable": brand_col,
            "not_empty": not_empty,
            "null_percentage": round(null_pct, 2),
            "properly_coded": has_labels,
            "distribution": distribution,
            "status": status,
            "message": "Brand variable validation complete."
        }
