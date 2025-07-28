import os
from datetime import datetime
import pandas as pd

# Configuration via environment variables
PROJECT = os.environ.get("GCP_PROJECT")  # e.g., "your-gcp-project-id"
DATASET = os.environ.get("BQ_DATASET", "rare_bird")
CHECKLIST_TABLE = os.environ.get("BQ_CHECKLIST_TABLE", "checklists")
PREDICTION_TABLE = os.environ.get("BQ_PREDICTION_TABLE", "predictions")

# Comma-separated species codes
SPECIES_LIST = os.environ.get("SPECIES_LIST", "black_swift").split(",")
FREQ_THRESHOLD = float(os.environ.get("FREQ_THRESHOLD", "0.05"))

def fetch_aggregated_data(species: str) -> pd.DataFrame:
    """
    Query BigQuery to get per-cell monthly checklist counts and species sightings.
    Buckets cells by rounding lat/lon to 1 decimal (~11km).
    """
    from google.cloud import bigquery

    bq_client = bigquery.Client()
    table_ref = f"`{PROJECT}.{DATASET}.{CHECKLIST_TABLE}`"
    sql = f"""
    SELECT
      ROUND(lat, 1) AS lat,
      ROUND(lng, 1) AS lon,
      EXTRACT(MONTH FROM obsDt) AS month,
      COUNT(DISTINCT subId) AS total_checklists,
      SUM(CASE WHEN speciesCode = @species THEN 1 ELSE 0 END) AS species_count
    FROM {table_ref}
    WHERE DATE(obsDt) >= DATE_SUB(CURRENT_DATE(), INTERVAL 5 YEAR)
    GROUP BY lat, lon, month
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("species", "STRING", species)]
    )
    df = bq_client.query(sql, job_config=job_config).to_dataframe()
    # Compute frequency and binary rare label
    df["freq"] = df["species_count"] / df["total_checklists"]
    df["is_rare"] = df["freq"] < FREQ_THRESHOLD
    return df

def train_model(df: pd.DataFrame):
    """Train an XGBoost classifier on historical aggregated data."""
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder
    from xgboost import XGBClassifier
    from sklearn.metrics import roc_auc_score

    features = ["lat", "lon", "month", "total_checklists"]
    X = df[features]
    y = df["is_rare"]

    # One-hot encode month
    preproc = ColumnTransformer(
        transformers=[
            ("month", OneHotEncoder(drop="if_binary"), ["month"])
        ],
        remainder="passthrough"
    )
    pipeline = Pipeline(
        steps=[
            ("preprocessor", preproc),
            ("classifier",
             XGBClassifier(
                 use_label_encoder=False,
                 eval_metric="logloss",
                 n_estimators=200,
                 learning_rate=0.1,
                 max_depth=5,
                 n_jobs=-1,
             )
            )
        ]
    )
    pipeline.fit(X, y)
    auc = roc_auc_score(y, pipeline.predict_proba(X)[:, 1])
    print(f"AUC: {auc:.3f}")
    return pipeline

def predict_current_month(pipeline, df: pd.DataFrame, species: str) -> pd.DataFrame:
    """Use the trained model to predict current-month rarity probabilities."""
    current_month = datetime.utcnow().month
    df_current = df[df["month"] == current_month].copy()
    if df_current.empty:
        return pd.DataFrame()

    features = ["lat", "lon", "month", "total_checklists"]
    X_cur = df_current[features]
    df_current["rarity_prob"] = pipeline.predict_proba(X_cur)[:, 1]
    df_current["species"] = species
    return df_current[["species", "lat", "lon", "rarity_prob", "month"]]

def write_to_bq(df: pd.DataFrame):
    """Load the concatenated prediction DataFrame into BigQuery, replacing old table."""
    from google.cloud import bigquery

    bq_client = bigquery.Client()
    table_id = f"{PROJECT}.{DATASET}.{PREDICTION_TABLE}"
    job = bq_client.load_table_from_dataframe(
        df,
        table_id,
        job_config=bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE)
    )
    job.result()  # Wait for completion

def main(request=None):
    all_preds = []
    for species in SPECIES_LIST:
        data = fetch_aggregated_data(species)
        model = train_model(data)
        preds = predict_current_month(model, data, species)
        if not preds.empty:
            all_preds.append(preds)

    if all_preds:
        result_df = pd.concat(all_preds, ignore_index=True)
        write_to_bq(result_df)
        print(f"Wrote predictions for species: {SPECIES_LIST}")
    else:
        print("No current-month data available for any species.")

if __name__ == "__main__":
    main()