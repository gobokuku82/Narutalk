# Data API Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/data_api /app/services/data_api
COPY shared /app/shared
COPY .env /app/.env

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8002

# Run the service
CMD ["python", "services/data_api/main.py"]