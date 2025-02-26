import sys
import json
import traceback
import importlib.util
from typing import Any, Dict, List, Optional
import logging
from pathlib import Path
import time
from question_models import TestCase, TestCaseResult, TestCaseIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SolutionLoader:
    """Handles loading and validating user submitted solutions"""

    def __init__(self, solution_path: str, function_name: str):
        self.solution_path = Path(solution_path)
        self.function_name = function_name
        self.solution_module = None

    def load_solution(self) -> Optional[Any]:
        """
        Dynamically loads the solution file and validates it has required function

        Returns:
            Optional[Any]: The solution function if found and valid
        """
        try:
            # Add typing imports to the module
            import typing
            import sys
            sys.modules['typing'] = typing

            # Create module spec from file path
            spec = importlib.util.spec_from_file_location(
                "solution_module",
                self.solution_path
            )
            if not spec or not spec.loader:
                raise ImportError("Failed to create module spec")

            # Create module and execute it
            self.solution_module = importlib.util.module_from_spec(spec)

            # Add typing to module namespace
            self.solution_module.List = typing.List

            spec.loader.exec_module(self.solution_module)

            # Get Solution class
            solution_class = getattr(self.solution_module, "Solution")

            # Instantiate solution and get the required method
            solution = solution_class()
            solution_func = getattr(solution, self.function_name)

            return solution_func

        except Exception as e:
            logger.error(f"Failed to load solution: {str(e)}")
            return None


class TestRunner:
    def __init__(self, solution_path: str, function_name: str):
        """
        Initialize the test runner

        Args:
            solution_path: Path to the Python file containing the Solution class
            function_name: Name of the function to test
        """
        self.solution_loader = SolutionLoader(solution_path, function_name)

    def run_single_test(self, test_case: TestCase) -> TestCaseResult:
        """
        Run a single test case

        Args:
            test_case: TestCase instance containing test data

        Returns:
            TestCaseResult: Results of the test execution
        """
        start_time = time.time()

        try:
            # Get solution function
            solution_func = self.solution_loader.load_solution()
            if not solution_func:
                raise Exception("Failed to load solution")

            # Execute the test
            actual_output = solution_func(*test_case.io_data.args)

            # Compare output
            success = actual_output == test_case.io_data.expected

            return TestCaseResult(
                test_case_id=test_case.id,
                success=success,
                actual_output=actual_output,
                error_message=None
            )

        except Exception as e:
            return TestCaseResult(
                test_case_id=test_case.id,
                success=False,
                actual_output=None,
                error_message=str(e)
            )

    def run_tests(self, test_cases: List[TestCase], mode: str = "run") -> Dict:
        """
        Run test cases based on mode

        Args:
            test_cases: List of TestCase instances
            mode: "run" for visible tests only, "submit" for all tests

        Returns:
            Dict: Summary of test execution results
        """
        # Filter test cases based on mode
        test_cases_to_run = [
            tc for tc in test_cases
            if mode == "submit" or tc.visible
        ]

        results = []
        passed_tests = 0
        start_time = time.time()

        for test_case in test_cases_to_run:
            result = self.run_single_test(test_case)
            results.append(result)
            if result.success:
                passed_tests += 1

        return {
            "total_tests": len(test_cases_to_run),
            "passed_tests": passed_tests,
            "failed_tests": len(test_cases_to_run) - passed_tests,
            "total_time": time.time() - start_time,
            "results": [result.__dict__ for result in results],
            "mode": mode
        }


def main():
    """Main entry point for the test runner"""
    if len(sys.argv) != 4:
        print("Usage: python test_runner.py <solution_file_path> <function_name> <test_cases_json_path>")
        sys.exit(1)

    solution_path = sys.argv[1]
    function_name = sys.argv[2]
    test_cases_path = sys.argv[3]

    # Read test cases from file
    with open(test_cases_path) as f:
        test_cases_json = f.read()

    try:
        # Parse test cases
        test_data = json.loads(test_cases_json)
        test_cases = [
            TestCase(
                io_data=TestCaseIO(
                    args=tc['inputs'],
                    expected=tc['expected']
                ),
                id=tc['id']
            ) for tc in test_data
        ]

        # Run tests
        runner = TestRunner(solution_path, function_name)
        summary = runner.run_tests(test_cases)

        # Output results in JSON format
        print(json.dumps(summary))

        # Exit with status code based on test success
        sys.exit(0 if summary["failed_tests"] == 0 else 1)

    except Exception as e:
        error_result = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main()
