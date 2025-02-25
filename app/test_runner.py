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
        # First, inject necessary imports into the solution file
        with open(file_path, 'r') as f:
            solution_code = f.read()

        # Add required imports at the beginning of the file
        imports = "from typing import List, Optional, Dict, Any\n\n"
        modified_code = imports + solution_code

        # Write the modified code back to a temporary file
        with open(file_path, 'w') as f:
            f.write(modified_code)

        # Import the solution file as a module
        spec = importlib.util.spec_from_file_location("test_module", file_path)
        if not spec or not spec.loader:
            return {"success": False, "error": "Failed to load test file"}

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Check for Solution class first
        solution_instance = None
        if hasattr(module, 'Solution'):
            solution_instance = module.Solution()

        # List all available attributes in the module
        module_contents = dir(module)
        print(f"Available module contents: {module_contents}", file=sys.stderr)

        # Check for different possible function names
        possible_names = ['two_sum', 'twoSum', 'TwoSum', 'twosum']
        function_name = None
        solution_func = None

        # First try to find method in Solution class
        if solution_instance:
            for name in possible_names:
                if hasattr(solution_instance, name):
                    function_name = name
                    solution_func = getattr(solution_instance, name)
                    break

        # If not found in class, look for module-level function
        if not solution_func:
            for name in possible_names:
                if hasattr(module, name):
                    function_name = name
                    solution_func = getattr(module, name)
                    break

        if not solution_func:
            return {
                "success": False,
                "error": f"Could not find solution function. Expected one of: {possible_names}. Found attributes: {module_contents}"
            }

        results = []
        successful_tests = 0
        total_tests = len(test_cases)

        for test_case in test_cases:
            try:
                input_params = test_case.get("input", [])
                target = test_case.get("target", 0)

                if solution_instance:
                    actual_output = solution_func(input_params, target)
                else:
                    actual_output = solution_func(input_params, target)

                is_valid = validate_output(actual_output, test_case)

                # Increment counter for successful tests
                if is_valid:
                    successful_tests += 1

                results.append({
                    "input": input_params,
                    "target": target,
                    "expected": test_case.get("output", []),
                    "actual": actual_output,
                    "success": is_valid,
                    "function_used": function_name
                })

            except Exception as e:
                results.append({
                    "input": input_params,
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "function_attempted": function_name
                })

        return {
            "success": successful_tests == total_tests,  # Only true if all tests pass
            "results": results,
            "function_found": function_name,
            "solution_type": "class" if solution_instance else "function",
            "test_summary": {
                "total": total_tests,
                "passed": successful_tests,
                "failed": total_tests - successful_tests
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def validate_output(actual_output: List[int], test_case: Dict) -> bool:
    expected_output = test_case.get('output', [])
    input_array = test_case.get('input', [])
    target = test_case.get('target', 0)

    # Check if output is a list of two integers
    if not isinstance(actual_output, list) or len(actual_output) != 2:
        return False

    # Check if indices are valid
    if not all(isinstance(i, int) and 0 <= i < len(input_array) for i in actual_output):
        return False

    # Check if numbers at these indices sum to target
    if input_array[actual_output[0]] + input_array[actual_output[1]] != target:
        return False

    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_runner.py <test_file> <test_cases_json>")
        sys.exit(1)

    test_file = sys.argv[1]
    test_cases = json.loads(sys.argv[2])

    # Print debugging information
    print(f"Test file path: {test_file}", file=sys.stderr)
    print(f"Test cases: {test_cases}", file=sys.stderr)

    results = run_test_file(test_file, test_cases)
    print(json.dumps(results))
