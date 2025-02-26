# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY app/testing/docker/requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy required files
COPY app/testing/test_runner.py /app/
COPY app/components/question_models.py /app/

# Create directory for test files
RUN mkdir -p /app/tests

# Set Python path
ENV PYTHONPATH=/app

# Make test runner executable
RUN chmod +x /app/test_runner.py

# Default command (can be overridden)
CMD ["python", "/app/test_runner.py"]