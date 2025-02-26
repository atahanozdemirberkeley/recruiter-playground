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

        # Print the code we're about to execute for debugging
        print(f"Executing code:\n{modified_code}", file=sys.stderr)

        # Import the solution file as a module
        try:
            spec = importlib.util.spec_from_file_location(
                "test_module", file_path)
            if not spec or not spec.loader:
                error_msg = "Failed to load test file"
                print(f"Error: {error_msg}", file=sys.stderr)
                return {"success": False, "error": error_msg}

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            error_msg = f"Error loading module: {str(e)}"
            print(f"Module loading error: {error_msg}", file=sys.stderr)
            print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
            return {"success": False, "error": error_msg, "traceback": traceback.format_exc()}

        # Check for Solution class first
        solution_instance = None
        if hasattr(module, 'Solution'):
            try:
                solution_instance = module.Solution()
                print(
                    f"Created Solution instance: {solution_instance}", file=sys.stderr)
            except Exception as e:
                error_msg = f"Error creating Solution instance: {str(e)}"
                print(error_msg, file=sys.stderr)
                return {"success": False, "error": error_msg, "traceback": traceback.format_exc()}

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
                    print(f"Found instance method: {name}", file=sys.stderr)
                    break
                elif hasattr(module.Solution, name):
                    # Check if it's a static/class method
                    function_name = name
                    solution_func = getattr(module.Solution, name)
                    print(
                        f"Found static/class method: {name}", file=sys.stderr)
                    break

        # If not found in class, look for module-level function
        if not solution_func:
            for name in possible_names:
                if hasattr(module, name):
                    function_name = name
                    solution_func = getattr(module, name)
                    print(f"Found module function: {name}", file=sys.stderr)
                    break

        if not solution_func:
            error_msg = f"Could not find solution function. Expected one of: {possible_names}. Found attributes: {module_contents}"
            print(f"Error: {error_msg}", file=sys.stderr)
            return {"success": False, "error": error_msg}

        results = []
        successful_tests = 0
        total_tests = len(test_cases)

        for test_case in test_cases:
            try:
                input_params = test_case.get("input", [])
                target = test_case.get("target", 0)

                print(
                    f"Running test with input={input_params}, target={target}", file=sys.stderr)

                # Check if it's a static method or instance method
                if solution_instance and function_name in dir(solution_instance):
                    print(f"Calling as instance method", file=sys.stderr)
                    actual_output = solution_func(input_params, target)
                else:
                    print(f"Calling as static/module function", file=sys.stderr)
                    actual_output = solution_func(input_params, target)

                print(f"Test output: {actual_output}", file=sys.stderr)

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
                error_msg = f"Error executing test: {str(e)}"
                print(error_msg, file=sys.stderr)
                print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)

                results.append({
                    "input": test_case.get("input", []),
                    "target": test_case.get("target", 0),
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "function_attempted": function_name
                })

        return {
            "success": successful_tests == total_tests,
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
        error_msg = f"Unexpected error in test runner: {str(e)}"
        print(error_msg, file=sys.stderr)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        return {
            "success": False,
            "error": error_msg,
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
