import sys
import importlib.util
import json
import traceback
from typing import Any, Dict, List, Optional

def run_test_file(file_path: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Runs the test file with provided test cases and returns results.
    """
    try:
        # Import the test file as a module
        spec = importlib.util.spec_from_file_location("test_module", file_path)
        if not spec or not spec.loader:
            return {"success": False, "error": "Failed to load test file"}
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        results = []
        for test_case in test_cases:
            try:
                # Get input parameters
                input_params = test_case.get("input", [])
                target = test_case.get("target", None)
                expected_output = test_case.get("output", None)
                
                # Handle different function signatures
                if isinstance(input_params, list) and target is not None:
                    actual_output = module.two_sum(input_params, target)
                else:
                    actual_output = module.is_valid(input_params)
                
                success = actual_output == expected_output
                results.append({
                    "input": test_case.get("input"),
                    "expected": expected_output,
                    "actual": actual_output,
                    "success": success
                })
                
            except Exception as e:
                results.append({
                    "input": test_case.get("input"),
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "success": False
                })
                
        return {
            "success": all(r["success"] for r in results),
            "results": results
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_runner.py <test_file> <test_cases_json>")
        sys.exit(1)
        
    test_file = sys.argv[1]
    test_cases = json.loads(sys.argv[2])
    
    results = run_test_file(test_file, test_cases)
    print(json.dumps(results)) 