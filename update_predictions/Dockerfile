# --- update_predictions/Dockerfile ---
    FROM python:3.10-slim
    WORKDIR /app
    
    # 1️⃣ install *this* folder’s requirements
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt   # note: update_predictions/requirements.txt
    
    # 2️⃣ copy the service code
    COPY run_model.py main.py ./
    # --------------------------------------
    ENV PORT 8080
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]