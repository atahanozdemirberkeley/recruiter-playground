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
        """Ensure the Docker container exists, create if it doesn't"""
        try:
            self.client.containers.get(self.container_name)
        except docker.errors.NotFound:
            # Create a new container without using the -d flag
            self.client.containers.create(
                image=self.image_name,
                name=self.container_name,
                detach=True,  # Use the detach parameter instead of -d flag
                tty=True,
                command="tail -f /dev/null"  # Keep container running
            )

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
            # Copy solution file to container
            os.system(
                f"docker cp {test_file_path} {self.container_name}:/solution.py")
            os.system(
                f"docker cp app/test_runner.py {self.container_name}:/test_runner.py")

            # Execute tests with test cases as a command line argument
            test_cases_json = json.dumps(test_cases)
            exec_result = self.client.containers.exec_run(
                self.container_name,
                cmd=f"python test_runner.py solution.py '{test_cases_json}'",
                stream=True
            )

            # Collect output
            console_output = []
            for output in exec_result.output:
                console_output.append(output.decode())

            # Parse results
            results = json.loads("".join(console_output))

            return (
                results.get("success", False),
                results.get("results", {}),
                "".join(console_output)
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
