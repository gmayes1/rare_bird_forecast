from fastapi import FastAPI, HTTPException, Query, Depends, Security
from typing import List, Dict
import os
from google.cloud import bigquery
from pydantic import BaseModel
from fastapi.security.api_key import APIKeyHeader

app = FastAPI(
    title="Rare Bird Predictions API",
    description="Serves real-time rare bird occurrence probabilities from BigQuery",
)

# Initialize BigQuery client
BQ_CLIENT = bigquery.Client()
PROJECT = os.environ.get("GCP_PROJECT")  # e.g., "your-gcp-project-id"
DATASET = os.environ.get("BQ_DATASET", "rare_bird")
TABLE = os.environ.get("BQ_TABLE", "predictions")

# API Key authentication
API_KEY_NAME = "X-API-Key"
API_KEY = os.environ.get("API_KEY", "")

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def validate_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return api_key

class Prediction(BaseModel):
    lat: float
    lon: float
    rarity_prob: float
    species: str
    month: int
    elevation_m: int = None
    habitat_type: str = None

@app.get("/predictions", response_model=List[Prediction], dependencies=[Depends(validate_api_key)])
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
