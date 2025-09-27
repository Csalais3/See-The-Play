# backend/config.py
import os
from typing import Dict, Any

class Settings:
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Pulse Mock API
    PULSE_API_URL: str = os.getenv("PULSE_API_URL", "http://localhost:1339")
    
    # Database (if needed later)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./seetheplay.db")
    
    # ML Model Settings
    MODEL_UPDATE_INTERVAL: int = int(os.getenv("MODEL_UPDATE_INTERVAL", "30"))  # seconds
    PREDICTION_CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.65"))
    
    # Cedar Integration
    CEDAR_ENABLED: bool = os.getenv("CEDAR_ENABLED", "true").lower() == "true"
    CEDAR_API_KEY: str = os.getenv("CEDAR_API_KEY", "demo-key")
    
    # Live Updates
    WEBSOCKET_HEARTBEAT: int = int(os.getenv("WEBSOCKET_HEARTBEAT", "30"))
    EVENT_SIMULATION_SPEED: int = int(os.getenv("EVENT_SIMULATION_SPEED", "5"))  # seconds between events
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        return {
            "api_host": cls.API_HOST,
            "api_port": cls.API_PORT,
            "pulse_api_url": cls.PULSE_API_URL,
            "database_url": cls.DATABASE_URL,
            "model_update_interval": cls.MODEL_UPDATE_INTERVAL,
            "prediction_confidence_threshold": cls.PREDICTION_CONFIDENCE_THRESHOLD,
            "cedar_enabled": cls.CEDAR_ENABLED,
            "websocket_heartbeat": cls.WEBSOCKET_HEARTBEAT,
            "event_simulation_speed": cls.EVENT_SIMULATION_SPEED,
            "log_level": cls.LOG_LEVEL
        }

settings = Settings()