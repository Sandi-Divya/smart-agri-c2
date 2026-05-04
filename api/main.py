from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import os
from datetime import datetime
from influxdb_client import InfluxDBClient

# ── App Setup ────────────────────────────────────────────
app = FastAPI(
    title="Smart Agriculture API - C2",
    description="C2 Data & Intelligence API for Smart Agriculture Platform",
    version="1.0.0"
)

# ── InfluxDB Setup ───────────────────────────────────────
INFLUX_URL = os.getenv("INFLUX_URL", "https://influxdb.cropwise.garden")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "my-super-secret-auth-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "smart_agri")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "sensor_data")

influx_client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)

# ── API Key Auth ─────────────────────────────────────────
API_KEY = os.getenv("API_KEY", "dev-api-key-c2")

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

# ── Models ───────────────────────────────────────────────
class IrrigationRequest(BaseModel):
    field_id: str
    crop_type: str
    soil_moisture: float
    temperature: float
    humidity: float

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    models_loaded: List[str]
    db_connected: bool
    kafka_broker: str

# ── Health Endpoint ──────────────────────────────────────
@app.get("/health")
def health_check():
    # Check InfluxDB connectivity
    try:
        health = influx_client.health()
        db_connected = health.status == "pass"
    except:
        db_connected = False

    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "models_loaded": [
            "yield_predictor_v1",
            "irrigation_optimizer_v1",
            "soil_moisture_forecaster_v1",
            "anomaly_detector_v1",
            "growth_stage_classifier_v1",
            "evapotranspiration_model_v1"
        ],
        "db_connected": db_connected,
        "kafka_broker": "kafka.cropwise.garden:9094"
    }

# ── Endpoints ────────────────────────────────────────────
@app.get("/predict/yield")
def predict_yield(
    field_id: str = "field1",
    api_key: str = Depends(verify_api_key)
):
    return {
        "field_id": field_id,
        "predicted_yield_kg_per_ha": 4250.75,
        "confidence": 0.87,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/optimize/irrigation")
def optimize_irrigation(
    request: IrrigationRequest,
    api_key: str = Depends(verify_api_key)
):
    growth = _get_growth_stage(request.field_id)
    et = _get_evapotranspiration(request.field_id)
    water_needed = max(0, et["etc_mm_per_day"] - (request.soil_moisture * 0.1))
    duration = int(water_needed * 6)
    return {
        "field_id": request.field_id,
        "recommended_water_mm": round(water_needed, 2),
        "irrigation_duration_mins": duration,
        "growth_stage": growth["growth_stage"],
        "evapotranspiration": et["etc_mm_per_day"],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/forecast/soil-moisture")
def forecast_soil_moisture(
    field_id: str = "field1",
    api_key: str = Depends(verify_api_key)
):
    return {
        "field_id": field_id,
        "current": 42.5,
        "forecast_24h": [41.2, 40.8, 39.5, 38.2, 37.8,
                         37.1, 36.5, 35.9, 35.2, 34.8,
                         34.1, 33.5, 33.0, 32.5, 32.1,
                         31.8, 31.5, 31.2, 30.9, 30.6,
                         30.3, 30.1, 29.9, 29.7],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/anomalies/sensors")
def get_anomalies(
    field_id: str = "field1",
    api_key: str = Depends(verify_api_key)
):
    return {
        "anomalies": [
            {
                "device_id": "esp32-01",
                "field_id": field_id,
                "parameter": "soil_moisture",
                "value": 95.0,
                "zscore": 4.2,
                "anomaly_type": "statistical_outlier",
                "detected_at": datetime.utcnow().isoformat() + "Z"
            }
        ],
        "total_count": 1,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/classify/growth-stage")
def classify_growth_stage(
    field_id: str = "field1",
    api_key: str = Depends(verify_api_key)
):
    return _get_growth_stage(field_id)

@app.get("/compute/evapotranspiration")
def compute_evapotranspiration(
    field_id: str = "field1",
    api_key: str = Depends(verify_api_key)
):
    return _get_evapotranspiration(field_id)

@app.get("/satellite/ndvi")
def get_ndvi(
    field_id: str = "field1",
    api_key: str = Depends(verify_api_key)
):
    return {
        "field_id": field_id,
        "ndvi": 0.72,
        "classification": "Healthy Vegetation",
        "captured_at": datetime.utcnow().isoformat() + "Z",
        "satellite": "Sentinel-2",
        "status": "pending_cr_integration"
    }

# ── Helpers ──────────────────────────────────────────────
def _get_growth_stage(field_id: str):
    return {
        "field_id": field_id,
        "growth_stage": "Vegetative",
        "stage_number": 2,
        "days_in_stage": 14,
        "kc": 0.85,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

def _get_evapotranspiration(field_id: str):
    return {
        "field_id": field_id,
        "et0_mm_per_day": 5.2,
        "kc": 0.85,
        "etc_mm_per_day": 4.42,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }