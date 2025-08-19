# Use a slim Python 3.10 image as the base
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Set up the Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# Install curl for the healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /app/src/static/images && \
    chmod -R 777 /app/src/static

# Expose the port the app will run on
EXPOSE 8890

# Define a healthcheck to verify the container is running and healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
CMD curl -f http://localhost:8890/health || exit 1

# Command to start the application when the container launches
CMD ["python", "run.py"]
