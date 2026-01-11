# app/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for some Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker cache
# The path is now simpler because the build context will be the 'app' directory
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create the directory for file uploads inside the container
RUN mkdir -p /app/uploads

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]