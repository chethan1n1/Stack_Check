from typing import Dict, Any, List

class QualityScoreEngine:
    @staticmethod
    def calculate_score(
        master_validation: Dict[str, Any],
        binary_validation: Dict[str, Any],
        metadata_validation: Dict[str, Any],
        duplicate_analysis: Dict[str, Any],
        datatype_validation: List[Dict[str, Any]],
        completeness_validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculates Quality Score out of 100 with refined penalties:
        - Missing Core Variable: -10 pts each
        - Missing Optional Variable: -2 pts each
        - Binary PASS: 0 pts
        - Binary WARNING: -1 pt each
        - Binary FAIL: -5 pts each
        - Metadata Issue: -1 pt each (missing labels, inconsistent, empty labels, etc.)
        - Duplicates (IDs, Rows, or Brand Rows): -5 pts total if any exist
        - Data type mismatch: -5 pts each
        """
        score = 100.0
        penalties = []
        
        # 1. Missing Variables Penalties
        for issue in master_validation.get("issues", []):
            if issue.get("status") == "MISSING":
                is_core = issue.get("category", "Core") == "Core"
                is_required = issue.get("required", True)
                
                if is_required:
                    if is_core:
                        penalty = 10
                        desc = f"Missing Required Core Variable: {issue['variable']}"
                    else:
                        penalty = 2
                        desc = f"Missing Required Optional Variable: {issue['variable']}"
                else:
                    penalty = 2
                    desc = f"Missing Optional Variable: {issue['variable']}"
                    
                score -= penalty
                penalties.append({"description": desc, "value": -penalty})
                
        # 2. Binary Coding Penalties
        for issue in binary_validation.get("issues", []):
            severity = issue.get("severity")
            var_name = issue.get("variable")
            
            if severity == "WARNING":
                penalty = 1
                desc = f"Binary Coding Warning ({issue.get('detected_coding')}): {var_name}"
                score -= penalty
                penalties.append({"description": desc, "value": -penalty})
            elif severity == "FAIL":
                penalty = 5
                desc = f"Binary Coding Failure (Non-Binary): {var_name}"
                score -= penalty
                penalties.append({"description": desc, "value": -penalty})
                
        # 3. Metadata Issues Penalties
        for issue in metadata_validation.get("issues", []):
            penalty = 1
            desc = f"SPSS Metadata Warning ({issue.get('issue_type')}): {issue.get('variable')}"
            score -= penalty
            penalties.append({"description": desc, "value": -penalty})
            
        # 4. Duplicate Records Penalties
        has_duplicates = (
            duplicate_analysis.get("duplicate_respondents_count", 0) > 0 or
            duplicate_analysis.get("duplicate_rows_count", 0) > 0 or
            duplicate_analysis.get("duplicate_brand_rows_count", 0) > 0
        )
        if has_duplicates:
            penalty = 5
            desc = "Duplicate Respondent IDs or rows detected in dataset"
            score -= penalty
            penalties.append({"description": desc, "value": -penalty})
            
        # 5. Data Type Mismatches
        for issue in datatype_validation:
            penalty = 5
            desc = f"Data Type Mismatch ({issue['expected_type']} vs {issue['actual_type']}): {issue['variable']}"
            score -= penalty
            penalties.append({"description": desc, "value": -penalty})

        # 6. Common Missing Respondent Penalty
        missing_pct = completeness_validation.get("fully_missing_respondents_pct", 0.0)
        if missing_pct > 5.0:
            penalty = 5
            desc = f"Common Missing Respondents > 5% ({missing_pct}%)"
            score -= penalty
            penalties.append({"description": desc, "value": -penalty})
        elif missing_pct > 3.0:
            penalty = 3
            desc = f"Common Missing Respondents 3%-5% ({missing_pct}%)"
            score -= penalty
            penalties.append({"description": desc, "value": -penalty})
        elif missing_pct >= 1.0:
            penalty = 1
            desc = f"Common Missing Respondents 1%-3% ({missing_pct}%)"
            score -= penalty
            penalties.append({"description": desc, "value": -penalty})
            
        # Bind score between 0 and 100
        score = max(0.0, min(100.0, score))
        score = round(score, 1)
        
        # Determine Status
        if score >= 95.0:
            status = "Excellent"
        elif score >= 80.0:
            status = "Good"
        elif score >= 60.0:
            status = "Warning"
        else:
            status = "Failed"
            
        return {
            "score": score,
            "status": status,
            "penalties": penalties
        }
Definition = QualityScoreEngine
