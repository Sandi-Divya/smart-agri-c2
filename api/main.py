from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import os
from datetime import datetime

# ── App Setup ────────────────────────────────────────────
app = FastAPI(
    title="Smart Agriculture API",
    description="C2 Data & Intelligence API for Smart Agriculture Platform",
    version="1.0.0"
)

# ── API Key Auth ─────────────────────────────────────────
API_KEY = os.getenv("API_KEY", "dev-api-key-c2")

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

# ── Request/Response Models ───────────────────────────────
class IrrigationRequest(BaseModel):
    field_id: str
    crop_type: str
    soil_moisture: float
    temperature: float
    humidity: float

class IrrigationResponse(BaseModel):
    field_id: str
    recommended_water_mm: float
    irrigation_duration_mins: int
    growth_stage: str
    evapotranspiration: float
    timestamp: str

class YieldResponse(BaseModel):
    field_id: str
    predicted_yield_kg_per_ha: float
    confidence: float
    timestamp: str

class SoilMoistureResponse(BaseModel):
    field_id: str
    current: float
    forecast_24h: list
    timestamp: str

class AnomalyResponse(BaseModel):
    anomalies: list
    total_count: int
    timestamp: str

class GrowthStageResponse(BaseModel):
    field_id: str
    growth_stage: str
    stage_number: int
    days_in_stage: int
    timestamp: str

class EvapotranspirationResponse(BaseModel):
    field_id: str
    et0_mm_per_day: float
    kc: float
    etc_mm_per_day: float
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    models_loaded: list
    db_connected: bool

# ── Endpoints ────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health_check():
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
        "db_connected": True
    }

@app.get("/predict/yield", response_model=YieldResponse)
def predict_yield(
    field_id: str = "field1",
    api_key: str = Depends(verify_api_key)
):
    # Placeholder — will connect to MLflow model
    return {
        "field_id": field_id,
        "predicted_yield_kg_per_ha": 4250.75,
        "confidence": 0.87,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/optimize/irrigation", response_model=IrrigationResponse)
def optimize_irrigation(
    request: IrrigationRequest,
    api_key: str = Depends(verify_api_key)
):
    # Calls growth stage + ET internally
    growth = _get_growth_stage(request.field_id)
    et = _get_evapotranspiration(request.field_id)
    
    # Simple irrigation calculation
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

@app.get("/forecast/soil-moisture", response_model=SoilMoistureResponse)
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

@app.get("/anomalies/sensors", response_model=AnomalyResponse)
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

@app.get("/classify/growth-stage", response_model=GrowthStageResponse)
def classify_growth_stage(
    field_id: str = "field1",
    api_key: str = Depends(verify_api_key)
):
    return _get_growth_stage(field_id)

@app.get("/compute/evapotranspiration", response_model=EvapotranspirationResponse)
def compute_evapotranspiration(
    field_id: str = "field1",
    api_key: str = Depends(verify_api_key)
):
    return _get_evapotranspiration(field_id)

# ── Internal Helper Functions ─────────────────────────────
def _get_growth_stage(field_id: str):
    return {
        "field_id": field_id,
        "growth_stage": "Vegetative",
        "stage_number": 2,
        "days_in_stage": 14,
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