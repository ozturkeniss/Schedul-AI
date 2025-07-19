#!/usr/bin/env python3
"""
Online Learning Module
Gerçek pod placement sonuçlarını öğrenip model'i günceller
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from collections import defaultdict
import structlog

logger = structlog.get_logger()

class OnlineLearner:
    """Online learning for scheduler model"""
    
    def __init__(self, data_dir: str = "data/online_learning"):
        self.data_dir = data_dir
        self.feedback_file = os.path.join(data_dir, "feedback_data.json")
        self.performance_file = os.path.join(data_dir, "performance_metrics.json")
        self.model_updates_file = os.path.join(data_dir, "model_updates.json")
        
        # Create data directory
        os.makedirs(data_dir, exist_ok=True)
        
        # Performance tracking
        self.performance_metrics = self._load_performance_metrics()
        self.feedback_data = self._load_feedback_data()
        self.model_updates = self._load_model_updates()
        
        # Learning parameters
        self.min_samples_for_update = 50
        self.accuracy_threshold = 0.7
        self.update_interval_hours = 24
        
        logger.info("Online learner initialized", 
                   data_dir=data_dir,
                   min_samples=self.min_samples_for_update)
    
    def _load_feedback_data(self) -> List[Dict[str, Any]]:
        """Feedback data'yı yükle"""
        try:
            if os.path.exists(self.feedback_file):
                with open(self.feedback_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error("Failed to load feedback data", error=str(e))
            return []
    
    def _save_feedback_data(self):
        """Feedback data'yı kaydet"""
        try:
            with open(self.feedback_file, 'w') as f:
                json.dump(self.feedback_data, f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to save feedback data", error=str(e))
    
    def _load_performance_metrics(self) -> Dict[str, Any]:
        """Performance metrics'i yükle"""
        try:
            if os.path.exists(self.performance_file):
                with open(self.performance_file, 'r') as f:
                    return json.load(f)
            return {
                "total_predictions": 0,
                "successful_predictions": 0,
                "accuracy": 0.0,
                "last_update": None,
                "daily_metrics": {}
            }
        except Exception as e:
            logger.error("Failed to load performance metrics", error=str(e))
            return {}
    
    def _save_performance_metrics(self):
        """Performance metrics'i kaydet"""
        try:
            with open(self.performance_file, 'w') as f:
                json.dump(self.performance_metrics, f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to save performance metrics", error=str(e))
    
    def _load_model_updates(self) -> List[Dict[str, Any]]:
        """Model update history'yi yükle"""
        try:
            if os.path.exists(self.model_updates_file):
                with open(self.model_updates_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error("Failed to load model updates", error=str(e))
            return []
    
    def _save_model_updates(self):
        """Model update history'yi kaydet"""
        try:
            with open(self.model_updates_file, 'w') as f:
                json.dump(self.model_updates, f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to save model updates", error=str(e))
    
    def add_feedback(self, prediction_result: Dict[str, Any], actual_node: str, 
                    success: bool, pod_status: str = "Running") -> Dict[str, Any]:
        """Pod placement sonucunu feedback olarak ekle"""
        try:
            timestamp = datetime.utcnow()
            
            # Feedback record oluştur
            feedback_record = {
                "timestamp": timestamp.isoformat(),
                "prediction": {
                    "predicted_node": prediction_result.get("predicted_node"),
                    "confidence": prediction_result.get("confidence", 0),
                    "algorithm": prediction_result.get("algorithm", "unknown"),
                    "ai_features": prediction_result.get("ai_features", {})
                },
                "actual": {
                    "actual_node": actual_node,
                    "success": success,
                    "pod_status": pod_status
                },
                "features": self._extract_feedback_features(prediction_result, actual_node)
            }
            
            # Feedback data'ya ekle
            self.feedback_data.append(feedback_record)
            
            # Performance metrics güncelle
            self._update_performance_metrics(success)
            
            # Data'yı kaydet
            self._save_feedback_data()
            self._save_performance_metrics()
            
            logger.info("Feedback added", 
                       predicted_node=prediction_result.get("predicted_node"),
                       actual_node=actual_node,
                       success=success,
                       total_feedback=len(self.feedback_data))
            
            return {
                "success": True,
                "feedback_id": len(self.feedback_data),
                "total_feedback": len(self.feedback_data)
            }
            
        except Exception as e:
            logger.error("Failed to add feedback", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_feedback_features(self, prediction_result: Dict[str, Any], 
                                 actual_node: str) -> Dict[str, Any]:
        """Feedback için feature'ları çıkar"""
        try:
            ai_features = prediction_result.get("ai_features", {})
            pod_requirements = ai_features.get("pod_requirements", {})
            cluster_state = ai_features.get("cluster_state", {})
            
            # Actual node'u bul
            node_predictions = prediction_result.get("node_predictions", [])
            actual_node_data = None
            for node_pred in node_predictions:
                if node_pred.get("node_name") == actual_node:
                    actual_node_data = node_pred
                    break
            
            features = {
                "pod_cpu_request": pod_requirements.get("cpu_request", 0),
                "pod_memory_request": pod_requirements.get("memory_request", 0),
                "cluster_total_nodes": cluster_state.get("total_nodes", 1),
                "cluster_ready_nodes": cluster_state.get("ready_nodes", 1),
                "cluster_avg_cpu": cluster_state.get("avg_cpu_usage", 0),
                "cluster_avg_memory": cluster_state.get("avg_memory_usage", 0)
            }
            
            if actual_node_data:
                features.update({
                    "node_cpu_usage": actual_node_data.get("resource_score", 0),
                    "node_memory_usage": actual_node_data.get("stability_score", 0),
                    "node_ready": 1.0 if actual_node_data.get("readiness_score", 0) > 0.5 else 0.0,
                    "node_taint_count": 0,  # TODO: Extract from actual data
                    "stability_score": actual_node_data.get("stability_score", 0),
                    "avg_cpu_usage": 0,  # TODO: Extract from historical data
                    "avg_memory_usage": 0,  # TODO: Extract from historical data
                })
            
            return features
            
        except Exception as e:
            logger.error("Failed to extract feedback features", error=str(e))
            return {}
    
    def _update_performance_metrics(self, success: bool):
        """Performance metrics'i güncelle"""
        try:
            self.performance_metrics["total_predictions"] += 1
            if success:
                self.performance_metrics["successful_predictions"] += 1
            
            # Accuracy hesapla
            total = self.performance_metrics["total_predictions"]
            successful = self.performance_metrics["successful_predictions"]
            self.performance_metrics["accuracy"] = successful / total if total > 0 else 0.0
            
            # Daily metrics güncelle
            today = datetime.utcnow().date().isoformat()
            if today not in self.performance_metrics["daily_metrics"]:
                self.performance_metrics["daily_metrics"][today] = {
                    "predictions": 0,
                    "successful": 0,
                    "accuracy": 0.0
                }
            
            daily = self.performance_metrics["daily_metrics"][today]
            daily["predictions"] += 1
            if success:
                daily["successful"] += 1
            daily["accuracy"] = daily["successful"] / daily["predictions"]
            
            self.performance_metrics["last_update"] = datetime.utcnow().isoformat()
            
        except Exception as e:
            logger.error("Failed to update performance metrics", error=str(e))
    
    def should_update_model(self) -> bool:
        """Model güncellemesi gerekip gerekmediğini kontrol et"""
        try:
            # Yeterli feedback var mı?
            if len(self.feedback_data) < self.min_samples_for_update:
                return False
            
            # Son güncelleme zamanı kontrol et
            if self.model_updates:
                last_update = datetime.fromisoformat(self.model_updates[-1]["timestamp"])
                hours_since_update = (datetime.utcnow() - last_update).total_seconds() / 3600
                if hours_since_update < self.update_interval_hours:
                    return False
            
            # Accuracy threshold kontrol et
            current_accuracy = self.performance_metrics.get("accuracy", 0.0)
            if current_accuracy < self.accuracy_threshold:
                return True
            
            # Model drift kontrol et (basit implementasyon)
            recent_feedback = self.feedback_data[-self.min_samples_for_update:]
            recent_success = sum(1 for f in recent_feedback if f["actual"]["success"])
            recent_accuracy = recent_success / len(recent_feedback)
            
            if recent_accuracy < current_accuracy * 0.9:  # %10 düşüş
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to check model update condition", error=str(e))
            return False
    
    def prepare_training_data(self) -> List[Dict[str, Any]]:
        """Online learning için training data hazırla"""
        try:
            if not self.feedback_data:
                return []
            
            training_data = []
            
            for feedback in self.feedback_data:
                features = feedback.get("features", {})
                actual = feedback.get("actual", {})
                
                # Label: 1 if prediction was correct, 0 otherwise
                predicted_node = feedback["prediction"]["predicted_node"]
                actual_node = actual["actual_node"]
                label = 1 if predicted_node == actual_node else 0
                
                # Training record oluştur
                record = features.copy()
                record["selected_node"] = predicted_node
                record["node_name"] = actual_node
                record["label"] = label
                
                training_data.append(record)
            
            logger.info("Training data prepared", 
                       samples=len(training_data),
                       positive_samples=sum(1 for r in training_data if r["label"] == 1))
            
            return training_data
            
        except Exception as e:
            logger.error("Failed to prepare training data", error=str(e))
            return []
    
    def update_model(self, model) -> Dict[str, Any]:
        """Model'i online learning ile güncelle"""
        try:
            logger.info("Starting online model update")
            
            # Training data hazırla
            training_data = self.prepare_training_data()
            
            if len(training_data) < self.min_samples_for_update:
                return {
                    "success": False,
                    "error": f"Insufficient training data: {len(training_data)} < {self.min_samples_for_update}"
                }
            
            # Model'i eğit
            training_result = model.train(training_data)
            
            if training_result.get("success"):
                # Model update history'ye ekle
                update_record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "training_samples": len(training_data),
                    "accuracy": training_result.get("accuracy", 0),
                    "previous_accuracy": self.performance_metrics.get("accuracy", 0),
                    "improvement": training_result.get("accuracy", 0) - self.performance_metrics.get("accuracy", 0)
                }
                
                self.model_updates.append(update_record)
                self._save_model_updates()
                
                logger.info("Online model update completed", 
                           accuracy=training_result.get("accuracy"),
                           improvement=update_record["improvement"])
                
                return {
                    "success": True,
                    "accuracy": training_result.get("accuracy"),
                    "improvement": update_record["improvement"],
                    "training_samples": len(training_data)
                }
            else:
                return {
                    "success": False,
                    "error": training_result.get("error", "Training failed")
                }
                
        except Exception as e:
            logger.error("Online model update failed", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Performance özeti döndür"""
        return {
            "total_predictions": self.performance_metrics.get("total_predictions", 0),
            "successful_predictions": self.performance_metrics.get("successful_predictions", 0),
            "accuracy": self.performance_metrics.get("accuracy", 0.0),
            "feedback_count": len(self.feedback_data),
            "model_updates": len(self.model_updates),
            "last_update": self.performance_metrics.get("last_update"),
            "should_update": self.should_update_model(),
            "daily_metrics": self.performance_metrics.get("daily_metrics", {})
        }
    
    def get_recent_feedback(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Son feedback'leri döndür"""
        return self.feedback_data[-limit:] if self.feedback_data else []
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Eski feedback data'yı temizle"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            original_count = len(self.feedback_data)
            self.feedback_data = [
                f for f in self.feedback_data 
                if datetime.fromisoformat(f["timestamp"]) > cutoff_date
            ]
            
            removed_count = original_count - len(self.feedback_data)
            if removed_count > 0:
                self._save_feedback_data()
                logger.info("Cleaned old feedback data", 
                           removed_count=removed_count,
                           remaining_count=len(self.feedback_data))
                
        except Exception as e:
            logger.error("Failed to cleanup old data", error=str(e)) 