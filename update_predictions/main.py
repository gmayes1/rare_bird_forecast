# update_predictions/main.py
import os
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app = FastAPI(title="Update Predictions Service")

@app.get("/")
async def trigger_update(bg: BackgroundTasks):
    try:
        logging.info("Triggered update_predictions via HTTP")
        # Import the heavy module only when the endpoint is hit
        from run_model import main as run_model_main
        bg.add_task(run_model_main)
        return {"status": "success", "message": "Predictions update started"}
    except Exception as exc:
        logging.exception("Error during predictions update")
        raise HTTPException(status_code=500, detail=str(exc))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
    