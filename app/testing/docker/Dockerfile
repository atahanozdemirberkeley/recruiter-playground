# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY app/testing/docker/requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create directory for test files and set it as the working directory
WORKDIR /app/tests

# Copy required files to the correct locations
COPY app/testing/test_runner.py /app/
COPY app/components/question_models.py /app/

# Set Python path to include both /app and /app/tests
ENV PYTHONPATH=/app:/app/tests

# Ensure line endings are correct and file is executable
RUN dos2unix /app/test_runner.py && \
    chmod +x /app/test_runner.py

# Default command (can be overridden)
CMD ["python3", "/app/test_runner.py"]