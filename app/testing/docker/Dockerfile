# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY testing/docker/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy required files
COPY testing/test_runner.py /app/
COPY components/question_models.py /app/

# Create directory for test files
RUN mkdir -p /app/submissions

# Set Python path to include app directory
ENV PYTHONPATH=/app

# Set permissions
RUN chmod +x /app/test_runner.py

# Define entrypoint that accepts arguments
ENTRYPOINT ["python", "/app/test_runner.py"]