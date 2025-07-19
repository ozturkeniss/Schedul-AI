#!/usr/bin/env python3
"""
Configuration management for AI Scheduler
"""

import os
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class APIConfig:
    """API Server Configuration"""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False

@dataclass
class GoBackendConfig:
    """Go Backend Configuration"""
    url: str = "http://localhost:8080"
    timeout: int = 10

@dataclass
class MLConfig:
    """Machine Learning Configuration"""
    model_path: str = "models/scheduler_model.pkl"
    retrain_interval_hours: int = 24
    min_training_samples: int = 100
    confidence_threshold: float = 0.7

@dataclass
class LoggingConfig:
    """Logging Configuration"""
    level: str = "INFO"
    format: str = "json"

class Config:
    """Main configuration class"""
    
    def __init__(self):
        # API Configuration
        self.api = APIConfig(
            host=os.getenv('API_HOST', '0.0.0.0'),
            port=int(os.getenv('API_PORT', '5000')),
            debug=os.getenv('DEBUG', 'false').lower() == 'true'
        )
        
        # Go Backend Configuration
        self.go_backend = GoBackendConfig(
            url=os.getenv('GO_BACKEND_URL', 'http://localhost:8080'),
            timeout=int(os.getenv('GO_BACKEND_TIMEOUT', '10'))
        )
        
        # ML Configuration
        self.ml = MLConfig(
            model_path=os.getenv('MODEL_PATH', 'models/scheduler_model.pkl'),
            retrain_interval_hours=int(os.getenv('RETRAIN_INTERVAL_HOURS', '24')),
            min_training_samples=int(os.getenv('MIN_TRAINING_SAMPLES', '100')),
            confidence_threshold=float(os.getenv('CONFIDENCE_THRESHOLD', '0.7'))
        )
        
        # Logging Configuration
        self.logging = LoggingConfig(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            format=os.getenv('LOG_FORMAT', 'json')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'api': {
                'host': self.api.host,
                'port': self.api.port,
                'debug': self.api.debug
            },
            'go_backend': {
                'url': self.go_backend.url,
                'timeout': self.go_backend.timeout
            },
            'ml': {
                'model_path': self.ml.model_path,
                'retrain_interval_hours': self.ml.retrain_interval_hours,
                'min_training_samples': self.ml.min_training_samples,
                'confidence_threshold': self.ml.confidence_threshold
            },
            'logging': {
                'level': self.logging.level,
                'format': self.logging.format
            }
        }

# Global config instance
config = Config() 