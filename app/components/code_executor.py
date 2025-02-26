import docker
import os
import logging
import uuid
import time
from typing import Dict, Tuple
import tempfile
import shutil
import json
import inspect

logger = logging.getLogger(__name__)

# Define the base Solution class


class Solution:
    """Base class that student solutions will inherit from"""

    def __init__(self):
        self.results = {}

    def validate(self):
        """Validate solution structure - can be overridden by specific problems"""
        return True

    def get_solution_info(self):
        """Return information about the solution implementation"""
        return {
            "methods": [method for method in dir(self)
                        if callable(getattr(self, method)) and not method.startswith('__')],
            "attributes": [attr for attr in dir(self)
                           if not callable(getattr(self, attr)) and not attr.startswith('__')]
        }


class CodeExecutor:
    """Handles code execution using Docker Hub images"""

    def __init__(self):
        self.image_name = "python:3.9-slim"  # Standard image from Docker Hub
        self.client = docker.from_env()
        self.solution_class = Solution  # Store reference to Solution class

        # Ensure the image is available
        self._ensure_image_exists()

    def _ensure_image_exists(self):
        """Pull the specified image from Docker Hub if not already present"""
        try:
            self.client.images.get(self.image_name)
            logger.info(f"Image {self.image_name} already exists locally")
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling {self.image_name} from Docker Hub...")
            self.client.images.pull(self.image_name)
            logger.info(f"Successfully pulled {self.image_name}")
        except docker.errors.APIError as e:
            logger.error(f"Failed to pull image: {e}")
            raise

    def execute_tests(self, test_file_path: str, test_cases: list) -> Tuple[bool, Dict, str]:
        """Execute tests in an ephemeral Docker container with enhanced diagnostics"""
        container = None
        container_name = f"test_runner_{uuid.uuid4().hex[:8]}"

        try:
            logger.info(f"Creating container {container_name}")
            container = self.client.containers.create(
                image=self.image_name,
                name=container_name,
                detach=True,
                mem_limit="512m",
                network_mode="none",
                command="tail -f /dev/null"
            )

            logger.info(f"Starting container {container_name}")
            container.start()

            # Basic container check
            logger.info("Running basic container check...")
            check_result = container.exec_run(
                ["/bin/sh", "-c", "echo 'Container is working'"])
            logger.info(
                f"Container check: {check_result.exit_code} - {check_result.output.decode('utf-8')}")

            # Python check
            logger.info("Checking Python installation...")
            python_check = container.exec_run(
                ["/bin/sh", "-c", "python --version"])
            logger.info(
                f"Python check: {python_check.exit_code} - {python_check.output.decode('utf-8')}")

            # Create app directory
            logger.info(f"Creating /app directory...")
            mkdir_result = container.exec_run(
                ["/bin/sh", "-c", "mkdir -p /app"])
            logger.info(
                f"Mkdir result: {mkdir_result.exit_code} - {mkdir_result.output.decode('utf-8')}")

            # Create a temporary directory for test files
            temp_dir = tempfile.mkdtemp()
            try:
                # Create a simple test script to verify execution
                with open(os.path.join(temp_dir, "test_verify.py"), "w") as f:
                    f.write("""
import sys
print("Python execution verification")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print("Arguments:", sys.argv)
try:
    import json
    print("JSON module available")
    try:
        with open('test_cases.json', 'r') as f:
            data = json.load(f)
            print(f"Loaded {len(data)} test cases")
    except Exception as e:
        print(f"Error loading test cases: {e}")
except ImportError:
    print("JSON module not available")
print("Verification complete")
""")

                # Copy test file to temp directory
                test_file_name = os.path.basename(test_file_path)
                temp_test_path = os.path.join(temp_dir, test_file_name)
                shutil.copy2(test_file_path, temp_test_path)

                # Write test cases to a JSON file
                test_cases_path = os.path.join(temp_dir, "test_cases.json")
                with open(test_cases_path, 'w') as f:
                    json.dump(test_cases, f)

                # Create solution.py with the Solution class definition
                solution_path = os.path.join(temp_dir, "solution.py")
                with open(solution_path, 'w') as f:
                    f.write(inspect.getsource(Solution))

                logger.info(f"Copying files to container {container_name}")
                tar_stream = docker.utils.tar(temp_dir)
                container.put_archive('/app', tar_stream)

                # List files in /app
                ls_result = container.exec_run(
                    ["/bin/sh", "-c", "ls -la /app"])
                logger.info(
                    f"Files in /app: {ls_result.output.decode('utf-8')}")

                # Run verification script first
                logger.info("Running verification script...")
                verify_result = container.exec_run(
                    ["/bin/sh", "-c", "cd /app && python test_verify.py"],
                    stderr=True  # Capture stderr too
                )
                logger.info(
                    f"Verification exit code: {verify_result.exit_code}")
                logger.info(
                    f"Verification output: {verify_result.output.decode('utf-8')}")

                # Now run the actual test with stderr capture
                logger.info(f"Running tests in container {container_name}")
                shell_cmd = f"cd /app && python {test_file_name} -t test_cases.json"
                result = container.exec_run(
                    ["/bin/sh", "-c", shell_cmd],
                    stderr=True  # Capture stderr too
                )

                # Process results
                exit_code = result.exit_code
                output = result.output.decode('utf-8')

                logger.info(f"Command exit code: {exit_code}")
                logger.info(f"Command output: {output}")

                # Parse output to extract test results
                success = exit_code == 0
                results = self._parse_test_output(output)

                return success, results, output

            finally:
                shutil.rmtree(temp_dir)

        except Exception as e:
            logger.error(f"Error executing tests: {e}")
            return False, {}, str(e)

        finally:
            if container:
                try:
                    logger.info(f"Stopping container {container_name}")
                    container.stop(timeout=2)
                    logger.info(f"Removing container {container_name}")
                    container.remove(force=True)
                except Exception as e:
                    logger.error(f"Error cleaning up container: {e}")

    def _parse_test_output(self, output: str) -> Dict:
        """Parse test output into structured results"""
        # Implement based on your test output format
        results = {
            "passed": output.count("PASS"),
            "failed": output.count("FAIL"),
            "errors": output.count("ERROR"),
        }
        return results

    def run_code(self, test_file_path: str, test_cases: list, mode: str = "run") -> Dict:
        """
        Run code against test cases and return formatted results

        Args:
            test_file_path: Path to the test file
            test_cases: List of test cases to run
            mode: Either "run" (visible tests only) or "submit" (all tests)

        Returns:
            Dict containing execution results
        """
        try:
            logger.info(f"Starting code execution in {mode} mode")
            logger.info(f"Using test file: {test_file_path}")
            logger.info(
                f"Selected {len(test_cases)} test cases for {mode} mode")

            # Execute tests
            logger.info("Executing tests...")
            success, results, console_output = self.execute_tests(
                test_file_path,
                test_cases
            )

            logger.info(
                f"Test execution completed - Success: {success}, "
                f"Results count: {len(results) if isinstance(results, dict) else 0} \n"
            )

            response = {
                "success": success,
                "results": results,
                "console_output": console_output,
                "mode": mode
            }
            logger.info(f"Console output: {console_output} \n")
            return response
        except Exception as e:
            logger.error(f"Error in run_code: {str(e)}")
            return {
                "success": False,
                "results": {},
                "console_output": f"Error executing code: {str(e)}",
                "mode": mode
            }
