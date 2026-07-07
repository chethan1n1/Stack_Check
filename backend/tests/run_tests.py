import sys
from backend.tests.test_parsers import test_parse_csv_dataset, test_parse_specification_sheet
from backend.tests.test_validators import (
    test_profiling_validator_inferences,
    test_binary_mapping_patterns,
    test_quality_scoring,
    test_master_variable_validator_regex,
    test_master_variable_validator_module_mapping,
    test_self_service_module_discovery_and_auto_discovery
)

def run():
    print("Running StackCheck validation test suite manually...")
    tests = [
        ("test_parse_csv_dataset", test_parse_csv_dataset),
        ("test_parse_specification_sheet", test_parse_specification_sheet),
        ("test_profiling_validator_inferences", test_profiling_validator_inferences),
        ("test_binary_mapping_patterns", test_binary_mapping_patterns),
        ("test_quality_scoring", test_quality_scoring),
        ("test_master_variable_validator_regex", test_master_variable_validator_regex),
        ("test_master_variable_validator_module_mapping", test_master_variable_validator_module_mapping),
        ("test_self_service_module_discovery_and_auto_discovery", test_self_service_module_discovery_and_auto_discovery)
    ]
    
    passed_count = 0
    for name, func in tests:
        try:
            print(f"Running {name}... ", end="")
            func()
            print("PASS")
            passed_count += 1
        except Exception as e:
            print("FAIL")
            print(f"Error in {name}: {str(e)}")
            import traceback
            traceback.print_exc()
            
    print(f"\nResult: {passed_count}/{len(tests)} tests passed.")
    if passed_count == len(tests):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    run()
