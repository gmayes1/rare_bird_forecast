import os
import logging
from fastapi import FastAPI, HTTPException
from run_model import main as run_model_main

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Update Predictions Service")

@app.get("/")
async def update_predictions():
    try:
        logging.info("Triggered update_predictions via HTTP")
        run_model_main()
        return {"status": "success", "message": "Predictions updated"}
    except Exception as e:
        logging.exception("Error during predictions update")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)