import os
import pandas as pd
import numpy as np

def generate_mock_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "sample_dataset.csv")
    sav_path = os.path.join(base_dir, "sample_dataset.sav")
    
    # 1. Create a pandas DataFrame containing validation errors
    # - Duplicate respondent IDs (RESP_ID 1001 is duplicated)
    # - Non 0/1 binary coding (AWARE_COKE is 1/2; CEP_MORNING is Yes/No text)
    # - Data type mismatch (AGE is string text, expected Integer)
    # - Missing optional variable (IMG_MODERN is completely missing)
    data = {
        "RESP_ID": [1001, 1002, 1003, 1004, 1001, 1006, 1007, 1008, 1009, 1010],
        "BRAND": [1, 2, 3, 1, 2, 3, 1, 2, 3, 1],
        "AGE": ["25", "34", "18", "45", "Unknown", "22", "30", "55", "40", "29"],
        "GENDER": [1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
        "AWARE_COKE": [1, 2, 1, 1, 2, 1, 2, 1, 2, 1],          # Coded as 1/2 instead of 0/1
        "CEP_MORNING": ["Yes", "No", "Yes", "Yes", "No", "Yes", "No", "Yes", "No", "Yes"],  # Coded as Yes/No strings
        "IMG_REFRESH": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]          # Coded correctly as 0/1
    }
    
    df = pd.DataFrame(data)
    
    # Save as CSV
    df.to_csv(csv_path, index=False)
    print(f"Generated mock CSV dataset at: {csv_path}")
    
    # Save as SPSS SAV (if pyreadstat is installed)
    try:
        import pyreadstat
        
        # Metadata configuration
        # RESP_ID label is missing, other variables are labeled
        column_labels = [
            "", # RESP_ID missing label
            "Survey Stacked Brand Code",
            "Age of Respondent",
            "Gender of Respondent",
            "Spontaneous Awareness Coca-Cola",
            "CEP - Good in the morning",
            "Imagery - Is Refreshing"
        ]
        
        # Value labels mapping (GENDER: 1=Male, 2=Female)
        variable_value_labels = {
            "BRAND": {1.0: "Coca-Cola", 2.0: "Pepsi", 3.0: "Dr Pepper"},
            "GENDER": {1.0: "Male", 2.0: "Female"},
            "AWARE_COKE": {1.0: "Aware", 2.0: "Not Aware"}  # Inconsistent label, expected Yes/No
        }
        
        pyreadstat.write_sav(
            df,
            sav_path,
            column_labels=column_labels,
            variable_value_labels=variable_value_labels
        )
        print(f"Generated mock SPSS SAV dataset at: {sav_path}")
    except ImportError:
        print("pyreadstat not installed in current environment. Sav file generation skipped (CSV only).")

if __name__ == "__main__":
    # Ensure folder path exists
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    generate_mock_data()
