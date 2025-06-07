import os
import requests
import logging
from google.cloud import bigquery
from google.cloud import secretmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Initialize clients
bq_client = bigquery.Client()
secret_client = secretmanager.SecretManagerServiceClient()

def get_ebird_api_key():
    secret_name = os.environ.get("EBIRD_SECRET_NAME", "")
    if secret_name:
        response = secret_client.access_secret_version(request={"name": secret_name})
        return response.payload.data.decode("UTF-8")
    # Fallback to environment variable
    return os.environ.get("EBIRD_API_KEY", "")

def fetch_recent_sightings(region_code="US-AZ"):
    api_key = get_ebird_api_key()
    headers = {"X-eBirdApiToken": api_key}
    url = f"https://api.ebird.org/v2/data/obs/{region_code}/recent"
    params = {"maxResults": 500, "back": 1}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    sightings = response.json()
    logging.info(f"Fetched {len(sightings)} recent sightings for region {region_code}")
    return sightings

def write_to_bigquery(data):
    table_id = os.environ.get("BQ_TABLE_ID")  # e.g., "your-project.rare_bird.checklists"
    rows = [
        {
            "speciesCode": d.get("speciesCode"),
            "comName": d.get("comName"),
            "lat": d.get("lat"),
            "lng": d.get("lng"),
            "obsDt": d.get("obsDt"),
            "locationName": d.get("locName", "Unknown"),
            "howMany": d.get("howMany", 1),
            "subId": d.get("subId")
        }
        for d in data
    ]
    logging.info(f"Writing {len(rows)} sighting rows to BigQuery table {table_id}")
    errors = bq_client.insert_rows_json(table_id, rows)
    if errors:
        logging.error(f"BigQuery insertion errors: {errors}")

def main(request):
    """Entry point for Cloud Function."""
    try:
        logging.info("Starting fetch_checklists execution")
        sightings = fetch_recent_sightings()
        write_to_bigquery(sightings)
        logging.info("Completed fetch_checklists execution successfully")
        return "Success"
    except Exception:
        logging.exception("Error in fetch_checklists")
        raise