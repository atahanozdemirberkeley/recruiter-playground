import docker
import os
import logging
import uuid
from typing import Dict, Tuple
import tempfile
import shutil
import json
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class CodeExecutor:
    """Handles code execution using Docker Hub images"""

    def __init__(self):
        self.image_name = "python:3.9-slim"  # Standard image from Docker Hub
        self.client = docker.from_env()

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
        """Execute tests in an ephemeral Docker container"""
        try:
            # Create a unique container name
            container_name = f"test_runner_{uuid.uuid4().hex[:8]}"

            # Create a new container for this execution
            container = self.client.containers.run(
                image=self.image_name,
                name=container_name,
                detach=True,
                remove=True,  # Auto-remove when stopped
                mem_limit="512m",  # Memory limit
                network_mode="none"  # No network access for security
            )

            try:
                # Create a temporary directory for test files
                temp_dir = tempfile.mkdtemp()
                try:
                    # Copy test file to temp directory
                    test_file_name = os.path.basename(test_file_path)
                    temp_test_path = os.path.join(temp_dir, test_file_name)
                    shutil.copy2(test_file_path, temp_test_path)

                    # Write test cases to a JSON file
                    test_cases_path = os.path.join(temp_dir, "test_cases.json")
                    with open(test_cases_path, 'w') as f:
                        json.dump(test_cases, f)

                    # Copy files to container
                    tar_stream = docker.utils.tar(temp_dir)
                    container.put_archive('/app', tar_stream)

                    # Run tests in container
                    cmd = f"cd /app && python {test_file_name} -t test_cases.json"
                    result = container.exec_run(cmd)

                    # Process results
                    exit_code = result.exit_code
                    output = result.output.decode('utf-8')

                    # Parse output to extract test results
                    # (Implementation depends on your test output format)
                    success = exit_code == 0
                    results = self._parse_test_output(output)

                    return success, results, output

                finally:
                    # Clean up temp directory
                    shutil.rmtree(temp_dir)

            finally:
                # Container will auto-remove due to 'remove=True' parameter
                pass

        except Exception as e:
            logger.error(f"Error executing tests: {e}")
            return False, {}, str(e)

    def _parse_test_output(self, output: str) -> Dict:
        """Parse test output into structured results"""
        # Implement based on your test output format
        # This is a placeholder implementation
        results = {
            "passed": output.count("PASS"),
            "failed": output.count("FAIL"),
            "errors": output.count("ERROR"),
        }
        return results

    def cleanup(self):
        """Stop the container but don't remove it"""
        try:
            subprocess.run(["docker", "stop", self.container_name], check=True)
            logger.info(f"Container {self.container_name} stopped")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error stopping container: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error during cleanup: {str(e)}")

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
                f"Results count: {len(results) if isinstance(results, dict) else 0}"
            )

            response = {
                "success": success,
                "results": results,
                "console_output": console_output,
                "mode": mode
            }
            logger.debug(f"Full response: {response}")
            return response
        except Exception as e:
            logger.error(f"Error in run_code: {str(e)}")
            return {
                "success": False,
                "results": {},
                "console_output": f"Error executing code: {str(e)}",
                "mode": mode
            }
