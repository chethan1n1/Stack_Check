import os
import tempfile
import pandas as pd
from backend.app.parsers.data_parser import DataParser

def test_parse_csv_dataset():
    # Create temp CSV dataset
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        df_mock = pd.DataFrame({
            "RESP_ID": [1, 2, 3],
            "BRAND": [1, 2, 3]
        })
        df_mock.to_csv(tmp.name, index=False)
        tmp_name = tmp.name

    try:
        df, meta = DataParser.parse_dataset(tmp_name)
        assert len(df) == 3
        assert list(df.columns) == ["RESP_ID", "BRAND"]
        assert meta["file_type"] == "CSV"
        assert meta["variable_types"]["RESP_ID"] is not None
    finally:
        os.remove(tmp_name)

def test_parse_specification_sheet():
    # Create temp CSV specification sheet
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        spec_df = pd.DataFrame({
            "variable_name": ["RESP_ID", "BRAND", "AWARE_COKE"],
            "variable_label": ["Id", "Brand Code", "Coke Awareness"],
            "category": ["Core", "Brand", "Dependent"],
            "required": ["Yes", "Yes", "No"],
            "data_type": ["Integer", "Integer", "Numeric"],
            "is_binary": ["No", "No", "Yes"],
            "expected_values": ["", "", "0;1"],
            "value_labels": ["", "1=Coke; 2=Pepsi", "0=No; 1=Yes"]
        })
        spec_df.to_csv(tmp.name, index=False)
        tmp_name = tmp.name

    try:
        config = DataParser.parse_specification_sheet(tmp_name)
        assert len(config["variables"]) == 3
        
        vars_map = {v["name"]: v for v in config["variables"]}
        
        assert vars_map["RESP_ID"]["required"] is True
        assert vars_map["RESP_ID"]["category"] == "Core"
        
        assert vars_map["BRAND"]["value_labels"] == {"1": "Coke", "2": "Pepsi"}
        
        assert vars_map["AWARE_COKE"]["is_binary"] is True
        assert vars_map["AWARE_COKE"]["expected_values"] == [0, 1]
    finally:
        os.remove(tmp_name)
