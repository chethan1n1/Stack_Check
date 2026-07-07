import pandas as pd
from typing import Dict, Any, List
from backend.app.validators.base import BaseValidator

class SPSSMetadataValidator(BaseValidator):
    def validate(self) -> Dict[str, Any]:
        """
        Validates SPSS metadata components:
        - Missing variable labels
        - Empty value labels
        - Inconsistent value labels
        - Missing-value definition rules
        - Variable label coverage %
        """
        df = self.df
        metadata = self.metadata
        config = self.config
        
        issues = []
        
        # Extracted labels and types
        var_labels = metadata.get("variable_labels", {})
        value_labels = metadata.get("value_labels", {})
        missing_rules = metadata.get("missing_ranges", {})
        
        total_variables = len(df.columns)
        variables_with_labels = 0
        variables_missing_labels = 0
        variables_missing_value_labels = 0
        variables_missing_rules = 0
        
        # Core variables config lists to align checks
        config_vars = {v["name"]: v for v in config.get("variables", [])}
        
        for col in df.columns:
            # Check 1: Variable Label
            has_label = col in var_labels and str(var_labels[col]).strip() != ""
            if has_label:
                variables_with_labels += 1
            else:
                variables_missing_labels += 1
                # Only warn if it's in the spec or core config
                severity = "WARNING"
                issues.append({
                    "variable": col,
                    "issue_type": "MISSING_LABEL",
                    "details": "Variable has no description label defined in SPSS metadata.",
                    "severity": severity
                })
            
            # Check 2: Empty Value Labels for Categorical/Binary Variables
            # Categorical check: is it binary, is it brand, or does it have expected values?
            is_categorical = False
            spec = config_vars.get(col)
            if spec:
                is_categorical = spec.get("is_binary", False) or spec.get("expected_values") is not None or spec.get("category") in ["Brand", "CEP", "Imagery", "Dependent"]
            else:
                # If not in spec, infer based on unique values
                non_null = df[col].dropna()
                if len(non_null) > 0 and len(non_null.unique()) <= 10 and not pd.api.types.is_float_dtype(df[col]):
                    is_categorical = True
            
            if is_categorical:
                has_value_labels = col in value_labels and len(value_labels[col]) > 0
                if not has_value_labels:
                    variables_missing_value_labels += 1
                    issues.append({
                        "variable": col,
                        "issue_type": "EMPTY_VALUE_LABELS",
                        "details": "Categorical/binary variable has no value labels (mappings) assigned.",
                        "severity": "WARNING"
                    })
                
                # Check 3: Inconsistent Value Labels
                elif spec and spec.get("value_labels"):
                    expected_labels = spec["value_labels"]  # dict of {"0": "No", "1": "Yes"}
                    actual_labels = value_labels[col]      # dict of {"0": "No", "1": "Yes"}
                    
                    mismatch = False
                    for val, label in expected_labels.items():
                        # Standardize values to string representations of float/int for comparison
                        val_str = str(val)
                        if val_str in actual_labels:
                            if actual_labels[val_str].lower().strip() != label.lower().strip():
                                mismatch = True
                                break
                        else:
                            mismatch = True
                            break
                    
                    if mismatch:
                        expected_str = ", ".join([f"{k}={v}" for k, v in expected_labels.items()])
                        actual_str = ", ".join([f"{k}={v}" for k, v in actual_labels.items()])
                        issues.append({
                            "variable": col,
                            "issue_type": "INCONSISTENT_LABEL",
                            "details": f"SPSS value labels ({actual_str}) do not match expected labels ({expected_str}).",
                            "severity": "WARNING"
                        })
            
            # Check 4: Missing Value Rules
            # Standard DP practice represents missing values as -99, 99, 999 etc.
            # If those exist but no SPSS missing values rules are declared, raise warning
            has_missing_rule = col in missing_rules and len(missing_rules[col]) > 0
            if not has_missing_rule:
                # Check if the data contains common missing indicators (-99, 99, 999)
                non_null = df[col].dropna()
                common_missing_indicators = {-99, -9, 99, 999, 9999}
                found_indicators = []
                
                if pd.api.types.is_numeric_dtype(df[col]) and len(non_null) > 0:
                    for val in common_missing_indicators:
                        if val in non_null.values:
                            found_indicators.append(str(val))
                
                if found_indicators:
                    variables_missing_rules += 1
                    issues.append({
                        "variable": col,
                        "issue_type": "MISSING_VALUE_RULE",
                        "details": f"Data contains common missing indicators ({', '.join(found_indicators)}) but no SPSS missing value definitions are set.",
                        "severity": "WARNING"
                    })
            else:
                # Rules exist
                pass

            # Check 5: SPSS Naming Rules Compliance
            spss_reserved = {"ALL", "AND", "BY", "EQ", "GE", "GT", "LE", "LT", "NE", "NOT", "OR", "TO", "WITH"}
            naming_errors = []
            
            if len(col) > 64:
                naming_errors.append("Exceeds maximum SPSS length of 64 characters.")
            
            if col:
                first_char = col[0]
                if not (first_char.isalpha() or first_char in ["@", "#", "$"]):
                    naming_errors.append("Must start with a letter, '@', '#', or '$'.")
                
                # Check for invalid characters
                import string
                allowed_chars = string.ascii_letters + string.digits + "@#$_."
                invalid_chars = [char for char in col if char not in allowed_chars]
                if invalid_chars:
                    invalid_chars_unique = sorted(list(set(invalid_chars)))
                    naming_errors.append(f"Contains invalid characters: {', '.join([repr(c) for c in invalid_chars_unique])}.")
                
                if col[-1] in [".", "_"]:
                    naming_errors.append("Cannot end with a period or underscore.")
                
                if col.upper() in spss_reserved:
                    naming_errors.append(f"Is an SPSS reserved keyword: {col.upper()}.")
                    
            if naming_errors:
                issues.append({
                    "variable": col,
                    "issue_type": "SPSS_NAMING_COMPLIANCE",
                    "details": "SPSS Naming Violation: " + " ".join(naming_errors),
                    "severity": "WARNING"
                })

        coverage_pct = (variables_with_labels / total_variables) * 100 if total_variables > 0 else 100.0

        return {
            "coverage_pct": round(coverage_pct, 1),
            "total_variables": total_variables,
            "variables_with_labels": variables_with_labels,
            "variables_missing_labels": variables_missing_labels,
            "variables_missing_value_labels": variables_missing_value_labels,
            "variables_missing_rules": variables_missing_rules,
            "issues": issues
        }
