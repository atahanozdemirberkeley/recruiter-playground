import subprocess
import os
import logging
import time
from typing import Dict, List
import tempfile
import shutil
import importlib.util
import traceback
from utils.question_models import TestCase, Question

logger = logging.getLogger(__name__)


class CodeExecutor:
    """Handles code execution directly using local Python interpreter"""

    def __init__(self):
        """
        Initialize CodeExecutor by confirming Python interpreter availability
        """
        self.execution_count = {
            "run": 0,
            "submit": 0
        }
        self.execution_timer = {
            "run": 0,
            "submit": 0
        }
        CodeExecutor.cooldown_periods = {
            "run": 5,  # 5 seconds cooldown for run mode
            "submit": 30  # 30 seconds cooldown for submit mode
        }

        try:
            # Check if Python exists and get version
            result = subprocess.run(
                ["python3", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            self.python_version = result.stdout.strip()
            logger.info(f"Found Python interpreter: {self.python_version}")

            # Use python3 as primary command
            self.python_cmd = "python3"

        except (subprocess.SubprocessError, FileNotFoundError):
            try:
                # Try with python command if python3 fails
                result = subprocess.run(
                    ["python", "--version"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.python_version = result.stdout.strip()
                logger.info(f"Found Python interpreter: {self.python_version}")

                # Use python as primary command
                self.python_cmd = "python"

            except (subprocess.SubprocessError, FileNotFoundError) as e:
                logger.error(f"Failed to find Python interpreter: {e}")
                raise Exception("No Python interpreter found on system")

        # Extract major.minor version
        import re
        version_match = re.search(r'Python (\d+\.\d+)', self.python_version)
        if version_match:
            self.python_version_num = float(version_match.group(1))
            if self.python_version_num < 3.6:
                logger.warning(
                    f"Python version {self.python_version_num} is below recommended version 3.6")
        else:
            logger.warning("Could not determine Python version number")
            self.python_version_num = 0

        logger.info(
            f"CodeExecutor initialized with Python: {self.python_version}")

    def _prepare_test_payload(self, test_cases: List[TestCase], mode: str) -> List[Dict]:
        """
        Prepare test cases for execution

        Args:
            test_cases: List of TestCase objects
            mode: Either "run" (visible tests) or "submit" (all tests)

        Returns:
            List of test case dictionaries
        """
        return [{
            'id': tc.id,
            'inputs': tc.io_data.args,
            'expected': tc.io_data.expected,
            'visible': tc.visible
        } for tc in test_cases if mode == "submit" or tc.visible]

    def _load_module_from_file(self, file_path: str, module_name: str):
        """
        Dynamically load a Python module from a file path

        Args:
            file_path: Path to the Python file
            module_name: Name to give the module

        Returns:
            Loaded module object
        """
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def execute_tests(self, solution_path: str, test_cases: List[Dict], function_name: str) -> Dict:
        """
        Execute tests directly by importing the solution module

        Args:
            solution_path: Path to the solution.py file
            test_cases: List of test case dictionaries
            function_name: Name of the function to test

        Returns:
            Dict containing test results
        """
        try:
            # Load the solution module
            solution_module = self._load_module_from_file(
                solution_path, "solution")

            # Check if Solution class exists
            if not hasattr(solution_module, "Solution"):
                raise Exception("Solution class not found in solution file")

            # Instantiate Solution class
            solution = solution_module.Solution()

            # Check if the function exists in the Solution class
            if not hasattr(solution, function_name):
                raise Exception(
                    f"Function {function_name} not found in Solution class")

            # Run tests
            results = []
            passed_tests = 0
            failed_tests = 0
            total_time = 0

            for tc in test_cases:
                test_id = tc['id']
                inputs = tc['inputs']
                expected = tc['expected']

                start_time = time.time()
                try:
                    # Call the function with arguments
                    actual = getattr(solution, function_name)(*inputs)
                    success = actual == expected
                    error_msg = None

                    if success:
                        passed_tests += 1
                    else:
                        failed_tests += 1

                except Exception as e:
                    actual = None
                    success = False
                    error_msg = str(e) + "\n" + traceback.format_exc()
                    failed_tests += 1

                end_time = time.time()
                test_time = end_time - start_time
                total_time += test_time

                results.append({
                    'test_id': test_id,
                    'inputs': inputs,
                    'expected': expected,
                    'actual': actual,
                    'success': success,
                    'error': error_msg,
                    'time': test_time
                })

            # Prepare result
            return {
                'results': results,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'total_tests': len(test_cases),
                'total_time': total_time
            }

        except Exception as e:
            logger.error(f"Error executing tests: {e}")
            raise

    def run_code(
        self,
        test_file_path: str,
        question: Question,
        mode: str = "run"
    ) -> Dict:
        """
        Execute code against test cases using local Python interpreter

        Args:
            test_file_path: Path to user's solution file
            question: Question object containing metadata
            mode: Either "run" (visible tests only) or "submit" (all tests)

        Returns:
            Dict containing execution results
        """
        temp_dir = None

        # Check if we need to enforce a cooldown period
        current_time = time.time()
        time_since_last_execution = current_time - \
            self.execution_timer.get(mode, 0)
        cooldown_period = CodeExecutor.cooldown_periods.get(mode, 0)

        if time_since_last_execution < cooldown_period:
            # If in cooldown period, return a response indicating this
            time_remaining = cooldown_period - time_since_last_execution
            logger.info(
                f"Cannot execute code in {mode} mode: cooldown period active ({time_remaining:.1f}s remaining)")
            return {
                'success': False,
                'cooldown': True,
                'time_remaining': round(time_remaining, 1),
                'error': f"Please wait {round(time_remaining, 1)} seconds before running code again in {mode} mode",
                'mode': mode
            }

        try:
            logger.info(f"Starting code execution in {mode} mode")

            # Select test cases based on mode
            test_cases = question.visible_test_cases if mode == "run" else question.all_test_cases

            # Prepare test cases
            test_case_dicts = self._prepare_test_payload(test_cases, mode)

            # Create a temp directory for the solution file
            temp_dir = tempfile.mkdtemp()

            # Copy the solution file to the temp directory
            temp_solution_path = os.path.join(temp_dir, 'solution.py')
            shutil.copy2(test_file_path, temp_solution_path)

            # Execute tests directly
            results = self.execute_tests(
                temp_solution_path,
                test_case_dicts,
                question.function_name
            )

            self.execution_count[mode] += 1
            # Update the execution timer for this mode
            self.execution_timer[mode] = time.time()

            return {
                'success': results['total_tests'] == results['passed_tests'],
                'results': {
                    'test_results': results['results'],
                    'summary': {
                        'total': results['total_tests'],
                        'passed': results['passed_tests'],
                        'failed': results['failed_tests'],
                        'execution_time': results['total_time']
                    }
                },
                'mode': mode
            }

        except Exception as e:
            logger.error(f"Error in run_code: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'mode': mode
            }

        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
