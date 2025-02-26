import os

# Docker execution service configuration
DOCKER_API_BASE_URL = os.getenv(
    'DOCKER_API_BASE_URL', 'tcp://localhost:2376')  # Default to localhost
DOCKER_IMAGE_NAME = "acilimeyva/python-test-runner:latest"
