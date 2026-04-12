FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    "openenv-core[core]>=0.2.1" \
    "fastapi>=0.100.0" \
    "uvicorn>=0.20.0" \
    "pydantic>=2.0.0" \
    "openai>=1.0.0"

# Copy the full project
COPY . .

# Set Python path so imports work
ENV PYTHONPATH=/app

# Critical: unbuffered output so [START]/[STEP]/[END] flush immediately to stdout
ENV PYTHONUNBUFFERED=1
ENV API_BASE_URL=https://api.groq.com/openai/v1
ENV MODEL_NAME=llama-3.3-70b-versatile

# HF Spaces expects port 7860
EXPOSE 7860

# Default: run inference.py (validator mode).
# To run the server instead, override with:
#   docker run ... your-image uvicorn server.app:app --host 0.0.0.0 --port 7860
CMD ["python", "-u", "inference.py"]


