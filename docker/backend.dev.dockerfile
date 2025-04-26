# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Configure poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --without dev --no-interaction --no-ansi

# Copy application code
COPY . .

# Create ytqa directory if it doesn't exist
RUN mkdir -p /app/ytqa

# Copy cookies file to the correct location
COPY cookies.txt /app/ytqa/cookies.txt

# Create cache directory
RUN mkdir -p /tmp/ytqa_cache

# Set environment variables
ENV PYTHONPATH=/app
ENV YTQA_CACHE_DIR=/tmp/ytqa_cache

# Expose port
EXPOSE 8000

# Run the application
CMD ["poetry", "run", "uvicorn", "ytqa.webapi.app:app", "--host", "0.0.0.0", "--port", "8000"] 