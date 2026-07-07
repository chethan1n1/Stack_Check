from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class DatasetMetadataSchema(BaseModel):
    filename: str
    file_size_mb: float
    file_type: str
    rows: int
    columns: int

class ProfilingSummarySchema(BaseModel):
    rows: int
    columns: int
    numeric_count: int
    string_count: int
    binary_count: int
    date_count: int
    potential_brand_variable: Optional[str] = None
    potential_respondent_id: Optional[str] = None

class MetadataIssueSchema(BaseModel):
    variable: str
    issue_type: str  # MISSING_LABEL, EMPTY_VALUE_LABELS, INCONSISTENT_LABEL, MISSING_VALUE_RULE
    details: str
    severity: str  # WARNING, FAIL

class MetadataSummarySchema(BaseModel):
    coverage_pct: float
    total_variables: int
    variables_with_labels: int
    variables_missing_labels: int
    variables_missing_value_labels: int
    variables_missing_rules: int
    issues: List[MetadataIssueSchema]

class MasterValidationIssueSchema(BaseModel):
    variable: str
    category: str
    status: str  # MISSING, UNEXPECTED
    required: bool

class MasterValidationSummarySchema(BaseModel):
    required_count: int
    found_count: int
    missing_count: int
    unexpected_count: int
    coverage_pct: float
    status: str  # PASS, FAIL
    issues: List[MasterValidationIssueSchema]

class BinaryIssueSchema(BaseModel):
    variable: str
    expected_coding: str
    detected_coding: str
    severity: str  # PASS, WARNING, FAIL
    suggested_fix: Optional[str] = None
    confidence_pct: float
    reason: Optional[str] = None

class BinarySummarySchema(BaseModel):
    pass_count: int
    warning_count: int
    fail_count: int
    auto_fix_opportunities: int
    issues: List[BinaryIssueSchema]

class NullVariableSchema(BaseModel):
    variable: str
    null_count: int
    null_pct: float
    blank_pct: float
    status: str  # GREEN, YELLOW, RED

class NullAnalysisSchema(BaseModel):
    green_count: int
    yellow_count: int
    red_count: int
    variables: List[NullVariableSchema]

class DuplicateAnalysisSchema(BaseModel):
    duplicate_respondents_count: int
    duplicate_rows_count: int
    duplicate_brand_rows_count: int
    respondent_id_col: Optional[str] = None
    brand_col: Optional[str] = None

class CoverageBandSchema(BaseModel):
    band: str
    respondents: int

class MissingRespondentSchema(BaseModel):
    respondent_id: Any
    country: Optional[str] = None
    brand: Optional[str] = None
    missing_analysis_variables: int
    missing_pct: float

class CompletenessValidationSchema(BaseModel):
    status: str  # INFO, WARNING, FAIL
    total_respondents: int
    total_analysis_variables: int
    fully_missing_respondents_count: int
    fully_missing_respondents_pct: float
    respondent_id_col: Optional[str] = None
    country_col: Optional[str] = None
    brand_col: Optional[str] = None
    analysis_variables: List[str]
    coverage_distribution: List[CoverageBandSchema]
    fully_missing_respondents: List[MissingRespondentSchema]
    quality_score_penalty: int
    quality_score_note: str

class EmptyVariableSchema(BaseModel):
    variable: str
    type: str  # EMPTY (100% Null/Blank) or CONSTANT (Constant Value)
    constant_value: Optional[str] = None

class DataTypeIssueSchema(BaseModel):
    variable: str
    expected_type: str
    actual_type: str
    status: str  # FAIL

class QualityScoreSchema(BaseModel):
    score: float
    status: str  # Excellent, Good, Warning, Failed
    penalties: List[Dict[str, Any]]

class ValidationResponseSchema(BaseModel):
    id: Optional[int] = None
    metadata: DatasetMetadataSchema
    profiling: ProfilingSummarySchema
    metadata_validation: MetadataSummarySchema
    master_validation: MasterValidationSummarySchema
    binary_validation: BinarySummarySchema
    completeness_validation: CompletenessValidationSchema
    null_analysis: NullAnalysisSchema
    duplicate_analysis: DuplicateAnalysisSchema
    empty_variables: List[EmptyVariableSchema]
    datatype_validation: List[DataTypeIssueSchema]
    quality_score: QualityScoreSchema
    final_status: str  # PASS, WARNING, FAIL
    mapping_review: Optional[Dict[str, Any]] = None
    audit_metadata: Optional[Dict[str, Any]] = None
    report_xlsx_url: Optional[str] = None
    report_pdf_url: Optional[str] = None
    report_json_url: Optional[str] = None
