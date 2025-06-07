from fastapi import FastAPI, HTTPException, Query
from typing import List, Dict
import os
from google.cloud import bigquery
from pydantic import BaseModel

app = FastAPI(
    title="Rare Bird Predictions API",
    description="Serves real-time rare bird occurrence probabilities from BigQuery",
)

# Initialize BigQuery client
BQ_CLIENT = bigquery.Client()
PROJECT = os.environ.get("GCP_PROJECT")  # e.g., "your-gcp-project-id"
DATASET = os.environ.get("BQ_DATASET", "rare_bird")
TABLE = os.environ.get("BQ_TABLE", "predictions")

class Prediction(BaseModel):
    lat: float
    lon: float
    rarity_prob: float
    species: str
    month: int
    elevation_m: int = None
    habitat_type: str = None

@app.get("/predictions", response_model=List[Prediction])
async def get_predictions(
    species: str = Query(..., description="Species code, e.g., black_swift"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12) filter")
) -> List[Dict]:
    # Build the query to fetch from BigQuery
    table_ref = f"`{PROJECT}.{DATASET}.{TABLE}`"
    query = f"""
        SELECT
            species,
            lat,
            lon,
            rarity_prob,
            month,
            elevation_m,
            habitat_type
        FROM {table_ref}
        WHERE species = @species AND month = @month
        ORDER BY rarity_prob DESC
        LIMIT 1000
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("species", "STRING", species),
            bigquery.ScalarQueryParameter("month", "INT64", month),
        ]
    )
    query_job = BQ_CLIENT.query(query, job_config=job_config)
    results = query_job.result()

    predictions = []
    for row in results:
        predictions.append({
            "species": row.species,
            "lat": row.lat,
            "lon": row.lon,
            "rarity_prob": row.rarity_prob,
            "month": int(row.month),
            "elevation_m": int(row.elevation_m) if row.elevation_m is not None else None,
            "habitat_type": row.habitat_type,
        })
    if not predictions:
        raise HTTPException(status_code=404, detail="No predictions found for given species/month.")
    return predictions
*** End of File

*** Begin File: predictions_api/requirements.txt
fastapi
uvicorn[standard]
google-cloud-bigquery
pydantic
*** End of File

*** Begin File: predictions_api/Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
# If you add other modules, copy them here

ENV PORT 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
*** End of File

*** Begin File: predictions_api/deploy.sh
#!/bin/bash
# Usage: bash deploy.sh <GCP_PROJECT_ID> <SERVICE_NAME>
PROJECT_ID="$1"
SERVICE_NAME="$2"
REGION="us-central1"

# Build and submit a container to Cloud Run
gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME}

gcloud run deploy ${SERVICE_NAME} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT=${PROJECT_ID},BQ_DATASET=rare_bird,BQ_TABLE=predictions
*** End of File

