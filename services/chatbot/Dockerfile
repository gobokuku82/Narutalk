# Chatbot Service Dockerfile
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
COPY services/chatbot /app/services/chatbot
COPY shared /app/shared
COPY .env /app/.env

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8001

# Run the service
CMD ["python", "services/chatbot/main.py"]