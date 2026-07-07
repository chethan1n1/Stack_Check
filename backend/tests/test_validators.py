import pandas as pd
from backend.app.validators.profiling_validator import ProfilingValidator
from backend.app.validators.spss_metadata_validator import SPSSMetadataValidator
from backend.app.validators.quality_score import QualityScoreEngine
from backend.app.validators.completeness_validator import CompletenessValidator
from backend.app.services.binary_mapping_service import BinaryMappingService
from backend.app.validators.master_val import MasterVariableValidator

def test_profiling_validator_inferences():
    df = pd.DataFrame({
        "RESPONDENT_ID": [1001, 1002, 1003],
        "BRAND_CODE": [1, 2, 1],
        "VAR_TEXT": ["a", "b", "c"]
    })
    metadata = {"variable_labels": {}, "value_labels": {}, "variable_types": {}}
    config = {"variables": []}
    
    profiler = ProfilingValidator(df, metadata, config)
    res = profiler.validate()
    
    assert res["rows"] == 3
    assert res["columns"] == 3
    assert res["potential_respondent_id"] == "RESPONDENT_ID"
    assert res["potential_brand_variable"] == "BRAND_CODE"

def test_binary_mapping_patterns():
    # Strict Pass
    s_pass = pd.Series([0, 1, 0, 1])
    res_pass = BinaryMappingService.analyze_binary_variable(s_pass)
    assert res_pass["status"] == "PASS"
    
    # Warning 1/2
    s_warn1 = pd.Series([1, 2, 1, 2])
    res_warn1 = BinaryMappingService.analyze_binary_variable(s_warn1)
    assert res_warn1["status"] == "WARNING"
    assert "1 -> 0" in res_warn1["suggested_fix"]
    
    # Warning Yes/No
    s_warn2 = pd.Series(["Yes", "No", "Yes"])
    res_warn2 = BinaryMappingService.analyze_binary_variable(s_warn2)
    assert res_warn2["status"] == "WARNING"
    assert "Yes -> 1" in res_warn2["suggested_fix"]
    
    # Fail - Multi state
    s_fail = pd.Series([0, 1, 2, 3])
    res_fail = BinaryMappingService.analyze_binary_variable(s_fail)
    assert res_fail["status"] == "FAIL"

def test_quality_scoring():
    # Mock validation states
    master_val = {"issues": [
        {"variable": "AGE", "category": "Core", "status": "MISSING", "required": True},
        {"variable": "OPT_VAR", "category": "Optional", "status": "MISSING", "required": False}
    ]}
    binary_val = {"issues": [
        {"variable": "AWARE_COKE", "severity": "WARNING", "detected_coding": "1, 2"},
        {"variable": "BAD_BIN", "severity": "FAIL", "detected_coding": "0,1,2,3"}
    ]}
    meta_val = {"issues": [
        {"variable": "RESP_ID", "issue_type": "MISSING_LABEL"}
    ]}
    dup_val = {"duplicate_respondents_count": 0, "duplicate_rows_count": 0, "duplicate_brand_rows_count": 0}
    type_val = []
    completeness_val = {"fully_missing_respondents_pct": 0.0}
    
    # Deductions:
    # Missing core: -10
    # Missing optional: -2
    # Binary warning: -1
    # Binary fail: -5
    # Metadata warning: -1
    # Total penalties expected: 10 + 2 + 1 + 5 + 1 = 19
    # Score expected: 100 - 19 = 81 (Good)
    
    score_res = QualityScoreEngine.calculate_score(master_val, binary_val, meta_val, dup_val, type_val, completeness_val)
    
    assert score_res["score"] == 81.0
    assert score_res["status"] == "Good"
    assert len(score_res["penalties"]) == 5

def test_completeness_validator_common_missing_respondents():
    df = pd.DataFrame({
        "RESPONDENT_ID": [1, 2, 3],
        "COUNTRY": ["US", "US", "UK"],
        "BRAND_CODE": [1, 1, 2],
        "IMG_TRUST": [None, 1, None],
        "IMG_TASTE": [None, None, None],
        "IMG_QUALITY": [None, 0, None],
        "IMG_INNOVATIVE": [None, 1, None],
    })

    config = {
        "variables": [
            {"name": "IMG_TRUST", "category": "Imagery", "is_analysis_variable": True},
            {"name": "IMG_TASTE", "category": "Imagery", "is_analysis_variable": True},
            {"name": "IMG_QUALITY", "category": "Imagery", "is_analysis_variable": True},
            {"name": "IMG_INNOVATIVE", "category": "Imagery", "is_analysis_variable": True},
        ]
    }

    validator = CompletenessValidator(
        df,
        metadata={},
        profile_config=config,
        respondent_id_col="RESPONDENT_ID",
        brand_col="BRAND_CODE",
        country_col="COUNTRY",
    )
    res = validator.validate()

    assert res["total_respondents"] == 3
    assert res["total_analysis_variables"] == 4
    assert res["fully_missing_respondents_count"] == 2
    assert res["fully_missing_respondents_pct"] == 66.67
    assert res["status"] == "FAIL"
    assert res["quality_score_penalty"] == 5

def test_master_variable_validator_regex():
    # Dataset has:
    # - "age" (exact match for "age", case-insensitive for "Age")
    # - "advocacy" (exact match for "advocacy")
    # - "advocacy_1" (should match regex "advocacy_.*")
    # - "advocacy_2" (should match regex "advocacy_.*")
    # - "some_other_col" (unexpected)
    df = pd.DataFrame({
        "age": [20, 25],
        "advocacy": [1, 0],
        "advocacy_1": [1, 1],
        "advocacy_2": [0, 1],
        "some_other_col": ["x", "y"]
    })
    
    # Expected config:
    # 1. "Age" - case-insensitive match for "age"
    # 2. "advocacy" - exact match for "advocacy" (should NOT match advocacy_1 or advocacy_2)
    # 3. "advocacy_.*" - regex match for "advocacy_1" and "advocacy_2"
    # 4. "missing_var" - missing core variable
    config = {
        "variables": [
            {"name": "Age", "category": "Core", "required": True},
            {"name": "advocacy", "category": "Core", "required": True},
            {"name": "advocacy_.*", "category": "Core", "required": True},
            {"name": "missing_var", "category": "Core", "required": True}
        ]
    }
    
    validator = MasterVariableValidator(df, {}, config)
    res = validator.validate()
    
    # 1. age matches Age (found 1)
    # 2. advocacy matches advocacy (found 2)
    # 3. advocacy_.* matches advocacy_1 (found 3) (advocacy_2 is also matched as we loop, wait, found_count counts how many expected variables are matched, which is 3)
    # 4. missing_var is missing
    
    assert res["found_count"] == 3
    assert res["missing_count"] == 1
    
    # Verify exact check vs substring/regex
    # "advocacy" should only match "advocacy", not "advocacy_"
    # Verify that "missing_var" is missing
    missing_vars = [i["variable"] for i in res["issues"] if i["status"] == "MISSING"]
    assert "missing_var" in missing_vars
    assert "advocacy" not in missing_vars
    assert "Age" not in missing_vars
    assert "advocacy_.*" not in missing_vars
    
    # Verify unexpected variables:
    # "some_other_col" should be unexpected
    unexpected_vars = [i["variable"] for i in res["issues"] if i["status"] == "UNEXPECTED"]
    assert "some_other_col" in unexpected_vars


def test_spss_metadata_naming_compliance():
    # Columns testing various naming compliance rules
    df = pd.DataFrame({
        "A": [1, 2],
        "A_VERY_LONG_VARIABLE_NAME_THAT_EXCEEDS_64_CHARACTERS_TO_TEST_SPSS_COMPLIANCE_RULE": [1, 2],
        "1_START_WITH_NUM": [1, 2],
        "VAR SPACE": [1, 2],
        "VAR-HYPHEN": [1, 2],
        "VAR_END_UNDER_": [1, 2],
        "VAR_END_PERIOD.": [1, 2],
        "ALL": [1, 2]
    })
    
    metadata = {
        "variable_labels": {},
        "value_labels": {},
        "missing_ranges": {}
    }
    config = {"variables": []}
    
    validator = SPSSMetadataValidator(df, metadata, config)
    res = validator.validate()
    
    issues = res["issues"]
    naming_issues = [i for i in issues if i["issue_type"] == "SPSS_NAMING_COMPLIANCE"]
    
    # We expect naming issues on the following columns:
    flagged_vars = {i["variable"] for i in naming_issues}
    
    assert "A_VERY_LONG_VARIABLE_NAME_THAT_EXCEEDS_64_CHARACTERS_TO_TEST_SPSS_COMPLIANCE_RULE" in flagged_vars
    assert "1_START_WITH_NUM" in flagged_vars
    assert "VAR SPACE" in flagged_vars
    assert "VAR-HYPHEN" in flagged_vars
    assert "VAR_END_UNDER_" in flagged_vars
    assert "VAR_END_PERIOD." in flagged_vars
    assert "ALL" in flagged_vars
    assert "A" not in flagged_vars


def test_master_variable_validator_module_mapping():
    # Dataset containing wildcard/pattern variables for modules
    df = pd.DataFrame({
        "CONSIDERATION_1": [1, 0],
        "CONSIDERATION_2": [1, 1],
        "IMAGERY_ATT_1": [0, 1],
        "some_random_col": ["x", "y"]
    })
    
    metadata = {}
    config = {
        "variables": [
            {"name": "Consideration", "category": "Core", "required": True},
            {"name": "Imagery", "category": "Core", "required": True},
            {"name": "CEP", "category": "Optional", "required": False}
        ]
    }
    
    validator = MasterVariableValidator(df, metadata, config)
    res = validator.validate()
    
    # In master_val.py:
    # "Consideration" expands to CONSIDERATION_.* (via config/module_mappings.json)
    # df has CONSIDERATION_1 and CONSIDERATION_2 -> both should be FOUND
    # "Imagery" expands to IMAGERY_.* -> does df.columns contain matches? 
    # Wait, IMAGERY_ATT_1 does match IMAGERY_.* !
    # "CEP" is missing
    
    assert res["found_count"] == 2  # Consideration and Imagery found
    assert res["missing_count"] == 1  # CEP missing (optional, but counts as missing optionally)
    
    found_vars = {i["variable"] for i in res["issues"] if i["status"] == "FOUND"}
    assert "CONSIDERATION_1" in found_vars
    assert "CONSIDERATION_2" in found_vars
    assert "IMAGERY_ATT_1" in found_vars
    
    # Verify module mappings summary in result
    mappings_summary = res["module_mappings"]
    consideration_summary = next(m for m in mappings_summary if m["business_module"] == "Consideration")
    assert consideration_summary["status"] == "FOUND"
    assert consideration_summary["match_count"] == 2
    
    cep_summary = next(m for m in mappings_summary if m["business_module"] == "CEP")
    assert cep_summary["status"] == "MISSING"
    assert cep_summary["match_count"] == 0


def test_auto_fix_service_recoding():
    import os
    import tempfile
    from backend.app.services.auto_fix_service import AutoFixService
    
    # 1. Create a temporary CSV file
    fd, temp_path = tempfile.mkstemp(suffix=".csv")
    try:
        df = pd.DataFrame({
            "VAR_1": [1, 2, 1, 2, 99],  # Non-standard binary coding (1/2), with 99
            "VAR_2": ["Yes", "No", "Yes", "No", "No"]  # Non-standard binary text coding
        })
        df.to_csv(temp_path, index=False)
        
        binary_issues = [
            {
                "variable": "VAR_1",
                "detected_coding": "1, 2",
                "severity": "WARNING",
                "suggested_fix": "1 -> 0; 2 -> 1"
            },
            {
                "variable": "VAR_2",
                "detected_coding": "Yes, No",
                "severity": "WARNING",
                "suggested_fix": "Yes -> 1; No -> 0"
            }
        ]
        
        # 2. Get impact of fixes
        impacts = AutoFixService.get_fixes_impact(temp_path, binary_issues)
        
        assert "VAR_1" in impacts
        # VAR_1 has 4 rows matching '1' or '2' out of 5 total rows
        assert impacts["VAR_1"]["affected_rows"] == 4
        assert impacts["VAR_1"]["affected_pct"] == 80.0
        assert impacts["VAR_1"]["severity"] == "MEDIUM"
        
        assert "VAR_2" in impacts
        assert impacts["VAR_2"]["affected_rows"] == 5
        assert impacts["VAR_2"]["affected_pct"] == 100.0
        assert impacts["VAR_2"]["severity"] == "HIGH"
        
        # 3. Apply fixes and save to new path
        fd_out, temp_out_path = tempfile.mkstemp(suffix=".csv")
        try:
            _, fixes_applied = AutoFixService.apply_fixes_and_save(
                dataset_path=temp_path,
                binary_issues=binary_issues,
                approved_variables=["VAR_1", "VAR_2"],
                output_path=temp_out_path
            )
            
            assert "VAR_1" in fixes_applied
            assert "VAR_2" in fixes_applied
            
            # Read back corrected file
            df_fixed = pd.read_csv(temp_out_path)
            
            # Verify VAR_1 has 1->0 and 2->1 recoded, 99 remains unchanged
            assert list(df_fixed["VAR_1"]) == [0, 1, 0, 1, 99]
            
            # Verify VAR_2 has "Yes"->1 and "No"->0
            assert list(df_fixed["VAR_2"]) == [1, 0, 1, 0, 0]
            
        finally:
            os.close(fd_out)
            if os.path.exists(temp_out_path):
                os.remove(temp_out_path)
    finally:
        os.close(fd)
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_self_service_module_discovery_and_auto_discovery():
    # Dataset containing variables for modules
    df = pd.DataFrame({
        "TRUST_1": [1, 2],
        "TRUST_2": [2, 1],
        "BRANDFAMILY_POWER": [1, 1],
        "CONS_1": [0, 1]
    })
    
    metadata = {}
    config = {
        "variables": [
            {"name": "Trust", "category": "Core", "required": True},
            {"name": "Demand Power", "category": "Core", "required": True},
            {"name": "Brand Love", "category": "Optional", "required": False}
        ],
        "module_mappings": [
            {
                "business_module": "Trust",
                "variable_pattern": "TRUST_.*",
                "required": True,
                "description": "Trust Questions"
            }
        ]
    }
    
    validator = MasterVariableValidator(df, metadata, config)
    res = validator.validate()
    
    resolution_report = res["module_resolution_report"]
    trust_res = next(r for r in resolution_report if r["business_module"] == "Trust")
    assert trust_res["source"] == "Excel Mapping"
    assert trust_res["matched_pattern"] == "TRUST_.*"
    assert "TRUST_1" in trust_res["matched_variables"]
    assert "TRUST_2" in trust_res["matched_variables"]
    assert trust_res["match_count"] == 2
    assert trust_res["status"] == "FOUND"

    brand_love_res = next(r for r in resolution_report if r["business_module"] == "Brand Love")
    assert brand_love_res["source"] == "Auto Discovery"
    assert brand_love_res["matched_pattern"] == "BRAND_LOVE_.*"
    assert brand_love_res["status"] == "UNKNOWN"
    assert brand_love_res["match_count"] == 0
    
    brand_love_issue = next(i for i in res["issues"] if i["variable"] == "Brand Love")
    assert brand_love_issue["status"] == "WARNING"
    assert brand_love_issue["reason"] == "Configuration Missing"
    
    unk_report = res["unknown_modules_report"]
    assert len(unk_report) == 1
    assert unk_report[0]["business_module"] == "Brand Love"
    assert unk_report[0]["suggested_pattern"] == "BRAND_LOVE_.*"

