FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY data/ ./data/
COPY static/ ./static/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 7860

# Run Flask app
CMD ["python", "src/app.py"]

