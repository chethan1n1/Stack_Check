import pandas as pd
from typing import Dict, Any, List

class BaseValidator:
    def __init__(self, df: pd.DataFrame, metadata: Dict[str, Any], config: Dict[str, Any]):
        """
        Args:
            df (pd.DataFrame): Dataset dataframe
            metadata (Dict[str, Any]): SPSS/file metadata
            config (Dict[str, Any]): Validation configuration (e.g. from ProjectProfile)
        """
        self.df = df
        self.metadata = metadata
        self.config = config

    def validate(self) -> Dict[str, Any]:
        """
        Executes validation. Must be implemented by subclasses.
        Returns a dictionary representing validation result structure.
        """
        raise NotImplementedError("Subclasses must implement validate()")
