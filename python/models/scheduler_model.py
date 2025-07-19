#!/usr/bin/env python3
"""
ML Model for Node Prediction
Random Forest ile node seçimi yapar
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import joblib
import os

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
import structlog

logger = structlog.get_logger()

class SchedulerModel:
    """ML Model for Kubernetes node prediction"""
    
    def __init__(self, model_path: str = "models/scheduler_model.pkl"):
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False
        self.last_training_time = None
        
        # Model parametreleri
        self.model_params = {
            'n_estimators': 100,
            'max_depth': 10,
            'random_state': 42,
            'n_jobs': -1
        }
        
        # Load existing model if available
        self._load_model()
    
    def _load_model(self):
        """Mevcut modeli yükle"""
        try:
            if os.path.exists(self.model_path):
                model_data = joblib.load(self.model_path)
                self.model = model_data['model']
                self.scaler = model_data['scaler']
                self.feature_names = model_data['feature_names']
                self.is_trained = model_data['is_trained']
                self.last_training_time = model_data['last_training_time']
                
                logger.info("Model loaded successfully", 
                           model_path=self.model_path,
                           is_trained=self.is_trained)
            else:
                logger.info("No existing model found, will train new model")
                
        except Exception as e:
            logger.error("Failed to load model", error=str(e))
    
    def _save_model(self):
        """Modeli kaydet"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'is_trained': self.is_trained,
                'last_training_time': self.last_training_time,
                'model_params': self.model_params
            }
            
            joblib.dump(model_data, self.model_path)
            logger.info("Model saved successfully", model_path=self.model_path)
            
        except Exception as e:
            logger.error("Failed to save model", error=str(e))
    
    def prepare_training_data(self, historical_data: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray]:
        """Training data hazırlar"""
        try:
            if not historical_data:
                logger.warning("No historical data provided for training")
                return np.array([]), np.array([])
            
            features = []
            labels = []
            
            for record in historical_data:
                # Feature extraction
                feature_vector = self._extract_features(record)
                if feature_vector is not None:
                    features.append(feature_vector)
                    
                    # Label: 1 if this node was selected, 0 otherwise
                    selected_node = record.get('selected_node')
                    current_node = record.get('node_name')
                    label = 1 if selected_node == current_node else 0
                    labels.append(label)
            
            if not features:
                logger.warning("No valid features extracted from historical data")
                return np.array([]), np.array([])
            
            X = np.array(features)
            y = np.array(labels)
            
            logger.info("Training data prepared", 
                       samples=len(X),
                       features=X.shape[1],
                       positive_samples=sum(y))
            
            return X, y
            
        except Exception as e:
            logger.error("Failed to prepare training data", error=str(e))
            return np.array([]), np.array([])
    
    def _extract_features(self, record: Dict[str, Any]) -> Optional[List[float]]:
        """Record'dan feature vector çıkarır"""
        try:
            # Pod requirements
            pod_cpu = record.get('pod_cpu_request', 0)
            pod_memory = record.get('pod_memory_request', 0)
            
            # Node features
            node_cpu_usage = record.get('node_cpu_usage', 0)
            node_memory_usage = record.get('node_memory_usage', 0)
            node_ready = 1.0 if record.get('node_ready', False) else 0.0
            node_taint_count = len(record.get('node_taints', []))
            
            # Historical features
            stability_score = record.get('stability_score', 0)
            avg_cpu_usage = record.get('avg_cpu_usage', 0)
            avg_memory_usage = record.get('avg_memory_usage', 0)
            
            # Cluster features
            cluster_total_nodes = record.get('cluster_total_nodes', 1)
            cluster_ready_nodes = record.get('cluster_ready_nodes', 1)
            cluster_avg_cpu = record.get('cluster_avg_cpu', 0)
            cluster_avg_memory = record.get('cluster_avg_memory', 0)
            
            # Feature vector
            features = [
                pod_cpu,
                pod_memory,
                node_cpu_usage,
                node_memory_usage,
                node_ready,
                node_taint_count,
                stability_score,
                avg_cpu_usage,
                avg_memory_usage,
                cluster_total_nodes,
                cluster_ready_nodes,
                cluster_avg_cpu,
                cluster_avg_memory
            ]
            
            # Feature names (for reference)
            if not self.feature_names:
                self.feature_names = [
                    'pod_cpu_request',
                    'pod_memory_request',
                    'node_cpu_usage',
                    'node_memory_usage',
                    'node_ready',
                    'node_taint_count',
                    'stability_score',
                    'avg_cpu_usage',
                    'avg_memory_usage',
                    'cluster_total_nodes',
                    'cluster_ready_nodes',
                    'cluster_avg_cpu',
                    'cluster_avg_memory'
                ]
            
            return features
            
        except Exception as e:
            logger.error("Feature extraction failed", error=str(e))
            return None
    
    def train(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Modeli eğitir"""
        try:
            logger.info("Starting model training", data_samples=len(historical_data))
            
            # Prepare training data
            X, y = self.prepare_training_data(historical_data)
            
            if len(X) == 0:
                return {
                    "success": False,
                    "error": "No valid training data available"
                }
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Create and train model
            self.model = RandomForestClassifier(**self.model_params)
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Update model state
            self.is_trained = True
            self.last_training_time = datetime.utcnow()
            
            # Save model
            self._save_model()
            
            # Training results
            results = {
                "success": True,
                "accuracy": accuracy,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "feature_count": X.shape[1],
                "model_params": self.model_params,
                "training_time": self.last_training_time.isoformat()
            }
            
            logger.info("Model training completed", 
                       accuracy=accuracy,
                       training_samples=len(X_train))
            
            return results
            
        except Exception as e:
            logger.error("Model training failed", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Node prediction yapar"""
        try:
            if not self.is_trained or self.model is None:
                logger.warning("Model not trained, using fallback prediction")
                return self._fallback_prediction(features)
            
            # Extract features
            feature_vector = self._extract_features(features)
            if feature_vector is None:
                return self._fallback_prediction(features)
            
            # Scale features
            X_scaled = self.scaler.transform([feature_vector])
            
            # Make prediction
            prediction = self.model.predict(X_scaled)[0]
            probabilities = self.model.predict_proba(X_scaled)[0]
            
            # Get feature importance
            feature_importance = dict(zip(self.feature_names, self.model.feature_importances_))
            
            return {
                "prediction": int(prediction),
                "confidence": float(max(probabilities)),
                "probabilities": probabilities.tolist(),
                "feature_importance": feature_importance,
                "model_used": "ml_model",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("ML prediction failed", error=str(e))
            return self._fallback_prediction(features)
    
    def _fallback_prediction(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback prediction (rule-based)"""
        try:
            # Simple rule-based prediction
            node_cpu_usage = features.get('node_cpu_usage', 0)
            node_memory_usage = features.get('node_memory_usage', 0)
            node_ready = features.get('node_ready', False)
            node_taint_count = len(features.get('node_taints', []))
            
            # Simple scoring
            score = 0
            if node_ready:
                score += 50
            if node_cpu_usage < 80:
                score += 25
            if node_memory_usage < 80:
                score += 25
            score -= node_taint_count * 10
            
            prediction = 1 if score > 50 else 0
            confidence = min(score / 100, 1.0)
            
            return {
                "prediction": prediction,
                "confidence": confidence,
                "probabilities": [1 - confidence, confidence],
                "feature_importance": {},
                "model_used": "fallback_rules",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Fallback prediction failed", error=str(e))
            return {
                "prediction": 0,
                "confidence": 0.0,
                "probabilities": [1.0, 0.0],
                "feature_importance": {},
                "model_used": "error_fallback",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Model bilgilerini döndürür"""
        return {
            "is_trained": self.is_trained,
            "model_path": self.model_path,
            "feature_count": len(self.feature_names),
            "feature_names": self.feature_names,
            "model_params": self.model_params,
            "last_training_time": self.last_training_time.isoformat() if self.last_training_time else None
        }
    
    def add_training_data(self, prediction_result: Dict[str, Any], actual_node: str) -> Dict[str, Any]:
        """Training data'ya yeni kayıt ekler"""
        try:
            # Bu fonksiyon gelecekte online learning için kullanılacak
            # Şimdilik sadece log tutuyoruz
            logger.info("Training data added", 
                       predicted_node=prediction_result.get('predicted_node'),
                       actual_node=actual_node,
                       confidence=prediction_result.get('confidence'))
            
            return {
                "success": True,
                "message": "Training data logged for future use"
            }
            
        except Exception as e:
            logger.error("Failed to add training data", error=str(e))
            return {
                "success": False,
                "error": str(e)
            } 