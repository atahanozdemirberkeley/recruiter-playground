import docker
import os
import logging
import uuid
import time
from typing import Dict, Tuple, List, Optional
import tempfile
import shutil
import json
import inspect
import requests
from dataclasses import asdict
from .question_models import TestCase, Question
from urllib.parse import urljoin
from config import DOCKER_IMAGE_NAME
import platform

logger = logging.getLogger(__name__)


class CodeExecutor:
    """Handles code execution via REST API to Docker container service"""

    def __init__(self):
        """
        Initialize CodeExecutor with Docker client configuration
        """
        try:
            # Initialize Docker client
            self.docker_client = docker.from_env()

            # Test connection
            self.docker_client.ping()
            logger.info("Successfully connected to Docker daemon")

        except docker.errors.DockerException as e:
            # If auto-detection fails, try common configurations
            if platform.system() == 'Linux':
                base_url = 'unix://var/run/docker.sock'
            else:
                # Windows/macOS typically use TCP
                base_url = 'tcp://localhost:2375'

            try:
                self.docker_client = docker.DockerClient(base_url=base_url)
                self.docker_client.ping()
                logger.info(f"Connected to Docker daemon at {base_url}")
            except docker.errors.DockerException as e:
                logger.error(f"Failed to connect to Docker daemon: {e}")
                raise

        self.image_name = DOCKER_IMAGE_NAME

        # Ensure we have the required image
        self._ensure_docker_image()

        logger.info(
            f"CodeExecutor initialized with Docker image: {self.image_name}")

    def _prepare_test_payload(self, test_cases: List[TestCase], mode: str) -> List[Dict]:
        """
        Prepare test cases for API payload

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

    def _setup_execution_environment(self, code_content: str, test_cases_json: str, function_name: str) -> Dict:
        """
        Set up the execution environment for the test runner

        Args:
            code_content: The user's code to test
            test_cases_json: JSON string of test cases
            function_name: Name of the function to test

        Returns:
            Dict containing container configuration and temp directory path
        """
        # Create temporary directory for test files
        temp_dir = tempfile.mkdtemp()

        try:
            # Write code to test file
            test_file = os.path.join(temp_dir, 'solution.py')
            with open(test_file, 'w') as f:
                f.write(code_content)

            # Write test cases to file
            test_cases_file = os.path.join(temp_dir, 'test_cases.json')
            with open(test_cases_file, 'w') as f:
                f.write(test_cases_json)

            # Container configuration
            container_config = {
                'image': self.image_name,
                'command': [
                    '/app/test_runner.py',
                    '/app/tests/solution.py',  # solution file path
                    function_name,             # function name
                    '/app/tests/test_cases.json'  # test cases file path
                ],
                'volumes': {
                    temp_dir: {
                        'bind': '/app/tests',
                        'mode': 'ro'  # Read-only mount
                    }
                },
                'detach': True,
                'remove': False,  # Don't auto-remove so we can get logs
                'network_disabled': True,  # Security: Disable network access
                'mem_limit': '512m'     # Limit memory usage
            }

            return container_config, temp_dir

        except Exception as e:
            shutil.rmtree(temp_dir)
            raise e

    def execute_tests(self, container_config: Dict) -> Dict:
        """
        Execute tests in a Docker container and return results

        Args:
            container_config: Container configuration dictionary

        Returns:
            Dict containing test results
        """
        # Ensure auto-remove is disabled so we can get logs
        container_config['remove'] = False
        container = None

        try:
            # Run the container
            container = self.docker_client.containers.run(**container_config)
            container_id = container.id
            logger.info(f"Started container with ID: {container_id}")

            # Wait for container to finish with timeout
            try:
                result = container.wait(timeout=30)

                # Immediately get logs after container finishes
                logs = container.logs(stdout=True, stderr=True)
                logs_decoded = logs.decode('utf-8')

                logger.info(f"DEBUG: Container logs: {logs_decoded}")
                # Don't treat failed tests as an error, only actual execution errors
                if result['StatusCode'] != 0:
                    raise Exception(f"Test execution failed: {logs_decoded}")

                # Try to parse the logs as JSON
                try:
                    return json.loads(logs_decoded)
                except json.JSONDecodeError:
                    logger.error(
                        f"Failed to parse container logs as JSON: {logs_decoded}")
                    raise Exception("Invalid test results format")

            except docker.errors.NotFound:
                logger.error(
                    f"Container {container_id} was removed before we could get logs")
                raise Exception("Container was removed before completion")

            except docker.errors.APIError as e:
                if "marked for removal" in str(e):
                    logger.error(
                        f"Container {container_id} was marked for removal")
                    # Try to get logs one last time
                    try:
                        logs = self.docker_client.api.logs(container_id)
                        return json.loads(logs.decode('utf-8'))
                    except:
                        raise Exception("Could not retrieve container logs")
                raise

        except Exception as e:
            logger.error(f"Error executing tests: {e}")
            raise

        finally:
            # Clean up container if it still exists
            if container:
                try:
                    # Force remove the container
                    container.remove(force=True)
                    logger.info(f"Cleaned up container {container_id}")
                except docker.errors.NotFound:
                    logger.info(f"Container {container_id} already removed")
                except Exception as e:
                    logger.error(f"Error removing container: {e}")

    def run_code(
        self,
        test_file_path: str,
        question: Question,
        mode: str = "run"
    ) -> Dict:
        """
        Execute code against test cases in Docker container

        Args:
            test_file_path: Path to user's solution file
            question: Question object containing metadata
            mode: Either "run" (visible tests only) or "submit" (all tests)

        Returns:
            Dict containing execution results
        """
        temp_dir = None
        try:
            logger.info(f"Starting code execution in {mode} mode")

            # Select test cases based on mode
            test_cases = question.visible_test_cases if mode == "run" else question.all_test_cases

            # Prepare test cases
            test_cases_json = json.dumps(
                self._prepare_test_payload(test_cases, mode))

            # Read the code file
            with open(test_file_path, 'r') as f:
                code_content = f.read()

            # Set up execution environment
            container_config, temp_dir = self._setup_execution_environment(
                code_content,
                test_cases_json,
                question.function_name
            )

            # Execute tests
            results = self.execute_tests(container_config)

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

    def _ensure_docker_image(self) -> None:
        """Ensure the required Docker image is available, pull if not"""
        try:
            self.docker_client.images.get(self.image_name)
            logger.info(f"Docker image {self.image_name} found locally")
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling Docker image {self.image_name}...")
            try:
                self.docker_client.images.pull(self.image_name)
                logger.info(f"Successfully pulled {self.image_name}")
            except docker.errors.APIError as e:
                logger.error(f"Failed to pull Docker image: {e}")
                raise
