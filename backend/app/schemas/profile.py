from pydantic import BaseModel, Field
from typing import Optional, List, Any

class VariableSpec(BaseModel):
    name: str = Field(..., description="Variable name in dataset")
    label: Optional[str] = Field(None, description="Expected variable label")
    category: str = Field("Core", description="Core, Brand, Dependent, CEP, Imagery, Strategic, or Optional")
    required: bool = Field(True, description="Is the variable required in the dataset?")
    data_type: str = Field("Numeric", description="Numeric, Integer, Float, String, Boolean, Date")
    is_binary: bool = Field(False, description="Should values be strictly binary 0/1?")
    expected_values: Optional[List[Any]] = Field(None, description="List of expected values, e.g. [0, 1] or [1, 2, 3]")
    value_labels: Optional[dict[str, str]] = Field(None, description="Expected value labels mapping, e.g., {'0': 'No', '1': 'Yes'}")

class ModuleMappingSpec(BaseModel):
    business_module: str = Field(..., description="Business module name")
    variable_pattern: str = Field(..., description="Regex pattern matching variables in dataset")
    required: bool = Field(True, description="Is this module required?")
    description: Optional[str] = Field(None, description="Description of the module")

class ProfileConfig(BaseModel):
    variables: List[VariableSpec]
    module_mappings: Optional[List[ModuleMappingSpec]] = Field(default=[], description="Self-service module mappings")

class ProjectProfileCreate(BaseModel):
    name: str
    description: Optional[str] = None
    config: ProfileConfig

class ProjectProfileResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    config: ProfileConfig
    
    class Config:
        from_attributes = True
        populate_by_name = True
