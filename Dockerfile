# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data/sessions data/uploads

# Set proper permissions
RUN chmod -R 755 /app

# Expose port 8080 (Cloud Run standard)
EXPOSE 8080

# No health check for now - let's eliminate all complexity
# HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
#     CMD curl -f http://localhost:$PORT/health || exit 1

# Use Gunicorn for production - required for Cloud Run
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 0 --preload wsgi:app