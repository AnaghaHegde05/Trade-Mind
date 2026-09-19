# Use Python 3.12 slim
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies.
# build-essential/gcc/g++ used to be required here to compile
# Prophet/XGBoost/LightGBM wheels; those packages were dropped from
# requirements.txt (see ml/pipelines.py), so the compiler toolchain is no
# longer needed. libpq-dev/git are kept for psycopg2/misc tooling.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
# Our folder structure matches: /app/backend
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . /app/backend

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
