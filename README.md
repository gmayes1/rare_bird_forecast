

# Rare Bird Forecasting Pipeline

This repository contains a fully automated, cloud-native pipeline for predicting and serving rare bird occurrence probabilities in Arizona.

## Overview

1. **fetch_checklists**:  
   - GCP Cloud Function that runs daily.  
   - Fetches recent eBird checklists for Arizona.  
   - Writes raw sightings to BigQuery (`rare_bird.checklists`).

2. **update_predictions**:  
   - Cloud Run service triggered nightly.  
   - Aggregates checklist data by grid cell and month.  
   - Trains or loads an XGBoost model per species.  
   - Writes prediction results to BigQuery (`rare_bird.predictions`).

3. **predictions_api**:  
   - Cloud Run service providing a FastAPI HTTP endpoint.  
   - Serves JSON predictions at `/predictions?species=<code>&month=<1-12>`.  
   - Reads from BigQuery `rare_bird.predictions`.

## Folder Structure

```
rare-bird-forecast/
├── fetch_checklists/       # Cloud Function source
├── update_predictions/     # Cloud Run model updater
├── predictions_api/        # Cloud Run FastAPI service
├── .gitignore
└── README.md
```

## Prerequisites

- GCP Project with:
  - BigQuery API enabled
  - Cloud Functions
  - Cloud Run
  - Cloud Scheduler
  - Secret Manager
- eBird API key (non-commercial use)
- `gcloud` CLI installed and authenticated

## Setup & Deployment

1. **Store eBird Key**  
   ```bash
   echo -n "YOUR_EBIRD_API_KEY" | \
     gcloud secrets create EBIRD_API_KEY \
       --replication-policy="automatic" \
       --data-file=-
   ```

2. **Deploy fetch_checklists**  
   ```bash
   cd fetch_checklists
   bash deploy.sh YOUR_GCP_PROJECT_ID fetch-checklists
   ```
   - Schedule via Cloud Scheduler (HTTP GET daily).

3. **Deploy update_predictions**  
   ```bash
   cd update_predictions
   bash deploy.sh YOUR_GCP_PROJECT_ID update-predictions
   ```
   - Schedule via Cloud Scheduler (HTTP GET nightly).

4. **Deploy predictions_api**  
   ```bash
   cd ../predictions_api
   bash deploy.sh YOUR_GCP_PROJECT_ID predictions-api
   ```

5. **Verify**  
   ```bash
   curl "https://<SERVICE_URL>/predictions?species=black_swift&month=6"
   ```

## Local Development

- Use Cloud Shell or local `gcloud` CLI to run and test each component.
- Adjust environment variables in `deploy.sh` as needed.

## License

MIT © [Your Name]