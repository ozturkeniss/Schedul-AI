#!/usr/bin/env python3
"""
AI Scheduler Flask API Server
Go backend'den veri alıp AI analizi yapar
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import structlog

# Add current directory to Python path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.processor import DataProcessor
from models.scheduler_model import SchedulerModel
from models.online_learner import OnlineLearner

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class AISchedulerAPI:
    """AI Scheduler Flask API Server"""
    
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for all routes
        
        # Configuration
        self.go_backend_url = os.getenv('GO_BACKEND_URL', 'http://localhost:8080')
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        
        # Data processor
        self.data_processor = DataProcessor()
        
        # ML Model
        self.ml_model = SchedulerModel()
        
        # Online Learner
        self.online_learner = OnlineLearner()
        
        # Register routes
        self._register_routes()
        
        logger.info("AI Scheduler API initialized", 
                   go_backend_url=self.go_backend_url,
                   debug=self.debug)
    
    def _register_routes(self):
        """Register API routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            try:
                # Check Go backend connectivity
                go_health = requests.get(f"{self.go_backend_url}/health", timeout=5)
                go_status = "healthy" if go_health.status_code == 200 else "unhealthy"
                
                return jsonify({
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "go_backend": go_status,
                    "version": "1.0.0"
                }), 200
            except Exception as e:
                logger.error("Health check failed", error=str(e))
                return jsonify({
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }), 500
        
        @self.app.route('/predict', methods=['POST'])
        def predict():
            """Predict optimal node for pod placement"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No data provided"}), 400
                
                # Extract pod info
                pod_name = data.get('pod_name')
                pod_namespace = data.get('pod_namespace')
                pod_spec = data.get('pod_spec', {})
                
                if not pod_name or not pod_namespace:
                    return jsonify({"error": "pod_name and pod_namespace required"}), 400
                
                logger.info("Prediction request received", 
                           pod_name=pod_name, 
                           pod_namespace=pod_namespace)
                
                # Get current cluster state from Go backend
                cluster_state = self._get_cluster_state()
                
                # Process cluster data
                processed_data = self.data_processor.process_cluster_state(cluster_state)
                
                # Extract AI features
                ai_features = self.data_processor.extract_ai_features(processed_data, pod_spec)
                
                # Use ML model for prediction
                prediction = self._ml_prediction(pod_name, pod_namespace, pod_spec, processed_data, ai_features)
                
                logger.info("Prediction completed", 
                           pod_name=pod_name,
                           predicted_node=prediction.get('node_name'),
                           confidence=prediction.get('confidence'))
                
                return jsonify(prediction), 200
                
            except Exception as e:
                logger.error("Prediction failed", error=str(e))
                return jsonify({"error": f"Prediction failed: {str(e)}"}), 500
        
        @self.app.route('/metrics', methods=['GET'])
        def get_metrics():
            """Get current cluster metrics from Go backend"""
            try:
                metrics = self._get_cluster_metrics()
                return jsonify(metrics), 200
            except Exception as e:
                logger.error("Failed to get metrics", error=str(e))
                return jsonify({"error": f"Failed to get metrics: {str(e)}"}), 500
        
        @self.app.route('/train', methods=['POST'])
        def train_model():
            """Trigger model training"""
            try:
                data = request.get_json() or {}
                historical_data = data.get('historical_data', [])
                
                logger.info("Model training requested", data_samples=len(historical_data))
                
                # Train model
                training_result = self.ml_model.train(historical_data)
                
                if training_result.get('success'):
                    return jsonify({
                        "status": "training_completed",
                        "accuracy": training_result.get('accuracy'),
                        "training_samples": training_result.get('training_samples'),
                        "timestamp": datetime.utcnow().isoformat()
                    }), 200
                else:
                    return jsonify({
                        "status": "training_failed",
                        "error": training_result.get('error'),
                        "timestamp": datetime.utcnow().isoformat()
                    }), 500
                    
            except Exception as e:
                logger.error("Model training failed", error=str(e))
                return jsonify({"error": f"Training failed: {str(e)}"}), 500
        
        @self.app.route('/data/summary', methods=['GET'])
        def get_data_summary():
            """Get processed data summary"""
            try:
                summary = self.data_processor.get_processed_data_summary()
                return jsonify(summary), 200
            except Exception as e:
                logger.error("Failed to get data summary", error=str(e))
                return jsonify({"error": f"Failed to get data summary: {str(e)}"}), 500
        
        @self.app.route('/data/features', methods=['POST'])
        def extract_features():
            """Extract AI features from request data"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No data provided"}), 400
                
                cluster_data = data.get('cluster_data', {})
                pod_spec = data.get('pod_spec', {})
                
                # Process cluster data
                processed_data = self.data_processor.process_cluster_state(cluster_data)
                
                # Extract AI features
                ai_features = self.data_processor.extract_ai_features(processed_data, pod_spec)
                
                return jsonify({
                    "processed_data": processed_data,
                    "ai_features": ai_features
                }), 200
                
            except Exception as e:
                logger.error("Feature extraction failed", error=str(e))
                return jsonify({"error": f"Feature extraction failed: {str(e)}"}), 500
        
        @self.app.route('/model/info', methods=['GET'])
        def get_model_info():
            """Get model information"""
            try:
                model_info = self.ml_model.get_model_info()
                return jsonify(model_info), 200
            except Exception as e:
                logger.error("Failed to get model info", error=str(e))
                return jsonify({"error": f"Failed to get model info: {str(e)}"}), 500
        
        @self.app.route('/feedback', methods=['POST'])
        def add_feedback():
            """Add feedback for pod placement result"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No data provided"}), 400
                
                prediction_result = data.get('prediction_result', {})
                actual_node = data.get('actual_node')
                success = data.get('success', False)
                pod_status = data.get('pod_status', 'Running')
                
                if not actual_node:
                    return jsonify({"error": "actual_node is required"}), 400
                
                result = self.online_learner.add_feedback(
                    prediction_result, actual_node, success, pod_status
                )
                
                return jsonify(result), 200 if result.get('success') else 500
                
            except Exception as e:
                logger.error("Failed to add feedback", error=str(e))
                return jsonify({"error": f"Failed to add feedback: {str(e)}"}), 500
        
        @self.app.route('/performance', methods=['GET'])
        def get_performance():
            """Get performance metrics"""
            try:
                performance = self.online_learner.get_performance_summary()
                return jsonify(performance), 200
            except Exception as e:
                logger.error("Failed to get performance", error=str(e))
                return jsonify({"error": f"Failed to get performance: {str(e)}"}), 500
        
        @self.app.route('/feedback/recent', methods=['GET'])
        def get_recent_feedback():
            """Get recent feedback"""
            try:
                limit = request.args.get('limit', 10, type=int)
                feedback = self.online_learner.get_recent_feedback(limit)
                return jsonify(feedback), 200
            except Exception as e:
                logger.error("Failed to get recent feedback", error=str(e))
                return jsonify({"error": f"Failed to get recent feedback: {str(e)}"}), 500
        
        @self.app.route('/online/update', methods=['POST'])
        def trigger_online_update():
            """Trigger online model update"""
            try:
                # Check if update is needed
                if not self.online_learner.should_update_model():
                    return jsonify({
                        "success": False,
                        "message": "No update needed at this time"
                    }), 200
                
                # Perform online update
                result = self.online_learner.update_model(self.ml_model)
                
                return jsonify(result), 200 if result.get('success') else 500
                
            except Exception as e:
                logger.error("Failed to trigger online update", error=str(e))
                return jsonify({"error": f"Failed to trigger online update: {str(e)}"}), 500
    
    def _get_cluster_state(self) -> Dict[str, Any]:
        """Get current cluster state from Go backend"""
        try:
            response = requests.get(f"{self.go_backend_url}/api/v1/metrics", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to get cluster state", error=str(e))
            return {}
    
    def _get_cluster_metrics(self) -> Dict[str, Any]:
        """Get cluster metrics from Go backend"""
        try:
            response = requests.get(f"{self.go_backend_url}/api/v1/metrics", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to get cluster metrics", error=str(e))
            return {"error": str(e)}
    
    def _ml_prediction(self, pod_name: str, pod_namespace: str, 
                      pod_spec: Dict, processed_data: Dict, ai_features: Dict) -> Dict[str, Any]:
        """ML model ile prediction yapar"""
        
        # Extract available nodes
        nodes = processed_data.get('nodes', [])
        if not nodes:
            return {
                "pod_name": pod_name,
                "pod_namespace": pod_namespace,
                "predicted_node": None,
                "confidence": 0.0,
                "reason": "No available nodes"
            }
        
        # ML predictions for each node
        node_predictions = []
        best_node = None
        best_confidence = -1
        
        for node in nodes:
            # Prepare features for ML model
            ml_features = {
                'pod_cpu_request': ai_features.get('pod_requirements', {}).get('cpu_request', 0),
                'pod_memory_request': ai_features.get('pod_requirements', {}).get('memory_request', 0),
                'node_cpu_usage': node.get('cpu_usage', 0),
                'node_memory_usage': node.get('memory_usage', 0),
                'node_ready': node.get('ready', False),
                'node_taints': node.get('taints', []),
                'stability_score': node.get('historical_features', {}).get('stability_score', 0),
                'avg_cpu_usage': node.get('historical_features', {}).get('avg_cpu_usage', 0),
                'avg_memory_usage': node.get('historical_features', {}).get('avg_memory_usage', 0),
                'cluster_total_nodes': ai_features.get('cluster_state', {}).get('total_nodes', 1),
                'cluster_ready_nodes': ai_features.get('cluster_state', {}).get('ready_nodes', 1),
                'cluster_avg_cpu': ai_features.get('cluster_state', {}).get('avg_cpu_usage', 0),
                'cluster_avg_memory': ai_features.get('cluster_state', {}).get('avg_memory_usage', 0)
            }
            
            # Get ML prediction
            ml_result = self.ml_model.predict(ml_features)
            
            node_prediction = {
                'node_name': node.get('name'),
                'ml_prediction': ml_result.get('prediction', 0),
                'ml_confidence': ml_result.get('confidence', 0),
                'ml_probabilities': ml_result.get('probabilities', [0, 0]),
                'model_used': ml_result.get('model_used', 'unknown'),
                'feature_importance': ml_result.get('feature_importance', {}),
                'resource_score': node.get('resource_score', 0),
                'readiness_score': node.get('readiness_score', 0),
                'stability_score': node.get('historical_features', {}).get('stability_score', 0)
            }
            
            node_predictions.append(node_prediction)
            
            # Select best node based on ML confidence
            if ml_result.get('prediction', 0) == 1 and ml_result.get('confidence', 0) > best_confidence:
                best_confidence = ml_result.get('confidence', 0)
                best_node = node.get('name')
        
        # If no ML model selected any node, use fallback
        if best_node is None:
            # Use enhanced scoring as fallback
            best_node = None
            best_score = -1
            
            for node in nodes:
                total_score = node.get('total_score', 0)
                if total_score > best_score:
                    best_score = total_score
                    best_node = node.get('name')
            
            best_confidence = min(best_score / 100.0, 1.0) if best_score > 0 else 0.0
        
        return {
            "pod_name": pod_name,
            "pod_namespace": pod_namespace,
            "predicted_node": best_node,
            "confidence": best_confidence,
            "reason": f"ML prediction with confidence: {best_confidence:.2f}",
            "algorithm": "ml_prediction",
            "node_predictions": node_predictions,
            "ai_features": {
                'pod_requirements': ai_features.get('pod_requirements', {}),
                'cluster_state': ai_features.get('cluster_state', {})
            }
        }
    
    def run(self, host='0.0.0.0', port=5000):
        """Run the Flask application"""
        logger.info("Starting AI Scheduler API", host=host, port=port)
        self.app.run(host=host, port=port, debug=self.debug)

def main():
    """Main entry point"""
    api = AISchedulerAPI()
    api.run()

if __name__ == '__main__':
    main() 