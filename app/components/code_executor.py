import docker
import os
import logging
from typing import Dict, Optional, Tuple
import json
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class CodeExecutor:
    """Handles code execution in a Docker container"""

    def __init__(self):
        self.container_name = "python_test_runner"
        self.image_name = "python:3.9-slim"
        self.client = docker.from_env()
        self._ensure_container_exists()

    def _ensure_container_exists(self):
        """Ensure the Docker container exists and is running"""
        try:
            container = self.client.containers.get(self.container_name)
            # If container exists but not running, start it
            if container.status != 'running':
                container.start()
                logger.info(
                    f"Started existing container {self.container_name}")
        except docker.errors.NotFound:
            # Create and start a new container
            container = self.client.containers.create(
                image=self.image_name,
                name=self.container_name,
                detach=True,
                tty=True,
                command="tail -f /dev/null"
            )
            container.start()
            logger.info(
                f"Created and started new container {self.container_name}")

    def execute_tests(self, test_file_path: str, test_cases: list) -> Tuple[bool, Dict, str]:
        """
        Execute tests in Docker container

        Args:
            test_file_path: Path to the file containing candidate's code
            test_cases: List of test cases from the question

        Returns:
            Tuple containing:
            - Success status (bool)
            - Test results (dict)
            - Console output (str)
        """
        try:
            # Verify and normalize paths
            test_file_path = os.path.abspath(test_file_path)
            test_runner_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), '..', 'test_runner.py'))

            logger.debug(f"Test file path: {test_file_path}")
            logger.debug(f"Test runner path: {test_runner_path}")

            # Verify files exist
            if not os.path.exists(test_file_path):
                logger.error(f"Test file not found at: {test_file_path}")
                return False, {}, "Test file not found"

            if not os.path.exists(test_runner_path):
                logger.error(f"Test runner not found at: {test_runner_path}")
                return False, {}, "Test runner not found"

            # Copy files to container with explicit paths
            cp_result = os.system(
                f"docker cp {test_file_path} {self.container_name}:/solution.py")
            if cp_result != 0:
                logger.error(
                    f"Failed to copy solution file. Command exit code: {cp_result}")
                return False, {}, "Failed to copy solution file to container"

            cp_result = os.system(
                f"docker cp {test_runner_path} {self.container_name}:/test_runner.py")
            if cp_result != 0:
                logger.error(
                    f"Failed to copy test runner. Command exit code: {cp_result}")
                return False, {}, "Failed to copy test runner to container"

            container = self.client.containers.get(self.container_name)

            # Verify files in container
            ls_result = container.exec_run(
                "ls -l /solution.py /test_runner.py")
            logger.debug(f"Files in container: {ls_result.output.decode()}")

            # First run the solution file directly to see any potential errors
            logger.info("Testing solution file execution...")
            solution_test = container.exec_run(
                "python /solution.py",
                stream=True
            )
            for output in solution_test.output:
                logger.info(f"Solution output: {output.decode()}")

            # Execute tests with test cases
            test_cases_json = json.dumps(test_cases)
            logger.info("Executing tests with test cases...")
            exec_result = container.exec_run(
                cmd=f"python /test_runner.py /solution.py '{test_cases_json}'",
                stream=True,
                demux=True  # Split stdout and stderr
            )

            # Collect both stdout and stderr
            stdout_output = []

            stderr_output = []

            for out, err in exec_result.output:
                if out:
                    decoded = out.decode()
                    stdout_output.append(decoded)
                    logger.info(f"Test stdout: {decoded}")
                if err:
                    decoded = err.decode()
                    stderr_output.append(decoded)
                    logger.error(f"Test stderr: {decoded}")

            # Combine stdout for JSON parsing
            full_output = "".join(stdout_output)

            # Log complete outputs
            if stderr_output:
                logger.error(
                    f"Complete stderr output: {''.join(stderr_output)}")
            logger.info(f"Complete stdout output: {full_output}")

            if not full_output.strip():
                error_msg = "No output received from test execution"
                if stderr_output:
                    error_msg += f"\nErrors: {''.join(stderr_output)}"
                logger.error(error_msg)
                return False, {}, error_msg

            try:
                results = json.loads(full_output)
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse output as JSON: '{full_output}'"
                if stderr_output:
                    error_msg += f"\nErrors: {''.join(stderr_output)}"
                logger.error(error_msg)
                return False, {}, error_msg

            return (
                results.get('success', False),
                {
                    'results': results.get('results', []),
                    'test_summary': results.get('test_summary', {})
                },
                full_output
            )

        except Exception as e:
            logger.error(f"Error executing tests: {e}")
            return False, {}, str(e)

    def cleanup(self):
        """Stop the container but don't remove it"""
        try:
            subprocess.run(["docker", "stop", self.container_name], check=True)
            logger.info(f"Container {self.container_name} stopped")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error stopping container: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error during cleanup: {str(e)}")
