# Backend-only Dockerfile for ECS Fargate
# This version doesn't include frontend files

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Expose port
EXPOSE 8000

# Initialize database and start server
CMD python -m src.db.init_db && \
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --log-level info
