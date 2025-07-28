# update_predictions/Dockerfile
FROM python:3.10-slim
WORKDIR /app

# Install OS dependencies for xgboost (OpenMP runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgomp1 libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY run_model.py .
COPY main.py .

ENV PORT 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]