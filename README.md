# AI-Enhanced Kubernetes Scheduler

An intelligent Kubernetes scheduler that combines Go backend with Python AI components to make advanced pod placement decisions using machine learning and historical data analysis.

## 🚀 Overview

This project implements an AI-enhanced Kubernetes scheduler that goes beyond traditional resource-based scheduling by incorporating:

- **Machine Learning Predictions**: Random Forest model for node selection
- **Historical Data Analysis**: 7-day pod metrics cache for stability scoring
- **Online Learning**: Continuous model improvement through feedback
- **Advanced Feature Engineering**: 13 different features for comprehensive analysis
- **Real-time Metrics**: Kubernetes Metrics API integration

## 🏗️ Architecture

### Components

1. **Go Backend (Port 8080)**
   - Kubernetes client integration
   - Metrics collection and caching
   - Node scoring algorithms
   - REST API endpoints

2. **Python AI (Port 5000)**
   - Machine learning model (Random Forest)
   - Feature engineering and data processing
   - Online learning with feedback loop
   - Prediction API

3. **Docker Compose**
   - Containerized deployment
   - Health checks and monitoring
   - Volume persistence for models and data

## 🔄 System Flow

### 1. Data Collection Phase
```
Kubernetes Cluster → Metrics API → Go Backend → PodMetricsCache
```

- Collects real CPU/Memory usage from Kubernetes Metrics API
- Caches pod metrics for 7 days with analysis
- Tracks pod restart rates, failure rates, and stability scores

### 2. Feature Engineering Phase
```
PodMetricsCache → DataProcessor → Feature Extraction → ML Model
```

- Extracts 13 different features:
  - Pod requirements (CPU/Memory requests)
  - Node usage (CPU/Memory utilization)
  - Cluster state (total nodes, ready nodes, averages)
  - Historical data (stability scores, failure rates)
  - Resource pressure and health scores

### 3. AI Prediction Phase
```
ML Model → Prediction → Confidence Score → Node Selection
```

- Random Forest model trained on historical data
- Provides confidence scores and feature importance
- Fallback to enhanced scoring if ML model unavailable

### 4. Online Learning Phase
```
Prediction → Feedback Collection → Performance Tracking → Model Updates
```

- Collects feedback on prediction accuracy
- Tracks daily performance metrics
- Updates model when performance degrades

## 🎯 Advanced Features vs Traditional Scheduler

### Traditional Kubernetes Scheduler
- Resource availability check
- Node taints/tolerations
- Pod/node affinity rules
- Simple scoring based on available resources

### AI-Enhanced Scheduler
- **13 Feature Analysis**: Comprehensive node evaluation
- **Historical Stability**: 7-day pod metrics analysis
- **ML Predictions**: Random Forest model with confidence scores
- **Online Learning**: Continuous improvement through feedback
- **Resource Pressure**: Advanced cluster health analysis
- **Failure Rate Prediction**: Historical pod analysis

## 🐳 Quick Start with Docker Compose

### Prerequisites
- Docker and Docker Compose
- `curl` and `jq` for testing

### 1. Start the System
```bash
# Clone the repository
git clone <repository-url>
cd ai-scheduler

# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

### 2. Run System Tests
```bash
# Make test script executable
chmod +x scripts/test_system.sh

# Run comprehensive tests
./scripts/test_system.sh
```

### 3. Quick Demo
```bash
# Make demo script executable
chmod +x scripts/demo.sh

# Run interactive demo
./scripts/demo.sh
```

### 4. Manual Testing

#### Test Go Backend
```bash
# Health check
curl http://localhost:8080/health

# Get node metrics
curl http://localhost:8080/api/v1/metrics | jq
```

#### Test Python AI
```bash
# Health check
curl http://localhost:5000/health

# Get model info
curl http://localhost:5000/model/info | jq

# Make a prediction
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "pod_name": "test-pod",
    "pod_namespace": "default",
    "pod_spec": {
      "containers": [{
        "name": "app",
        "resources": {
          "requests": {
            "cpu": "500m",
            "memory": "512Mi"
          }
        }
      }]
    }
  }' | jq

# Submit feedback
curl -X POST http://localhost:5000/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "prediction_result": {
      "predicted_node": "minikube",
      "confidence": 0.95,
      "algorithm": "ml_prediction"
    },
    "actual_node": "minikube",
    "success": true,
    "pod_status": "Running"
  }' | jq
```

## 📊 Test Results Example

### System Health
```json
{
  "go_backend": "healthy",
  "python_ai": "healthy",
  "accuracy": "100%",
  "total_predictions": 5,
  "successful_predictions": 5
}
```

### AI Prediction Response
```json
{
  "predicted_node": "minikube",
  "confidence": 1.0,
  "algorithm": "ml_prediction",
  "ai_features": {
    "pod_requirements": {"cpu_request": 0.5, "memory_request": 512.0},
    "cluster_state": {
      "avg_cpu_usage": 45.2,
      "avg_memory_usage": 62.8,
      "health_score": 100.0,
      "resource_pressure": 54.0
    }
  },
  "node_predictions": [
    {
      "node_name": "minikube",
      "resource_score": 0.4776,
      "readiness_score": 1.0,
      "stability_score": 1.0,
      "ml_confidence": 1.0
    }
  ]
}
```

## 🔧 Configuration

### Go Backend Config (`go/config/config.yaml`)
```yaml
server:
  host: "0.0.0.0"
  port: 8080
  read_timeout: 30s
  write_timeout: 30s

kubernetes:
  in_cluster: false
  kubeconfig_path: "~/.kube/config"

metrics:
  collection_interval: 30s
  cache_duration: 168h  # 7 days

scheduler:
  ai_api_url: "http://python-ai:5000"
  scoring:
    cpu_weight: 30.0
    memory_weight: 30.0
    node_ready_weight: 20.0
    taint_weight: 10.0
    failed_pods_weight: 5.0
    restart_weight: 5.0
```

### Python AI Config (`python/config/config.yaml`)
```yaml
server:
  host: "0.0.0.0"
  port: 5000

model:
  type: "random_forest"
  max_depth: 10
  n_estimators: 100
  random_state: 42

online_learning:
  feedback_threshold: 10
  performance_threshold: 0.8
  update_interval: 24h

data:
  cache_duration: 168h  # 7 days
  feature_count: 13
```

## 📈 Performance Metrics

### Key Performance Indicators
- **Accuracy**: 100% (5/5 successful predictions)
- **Response Time**: < 100ms for predictions
- **Model Confidence**: 1.0 (high confidence predictions)
- **Feature Importance**: 13 features analyzed
- **Online Learning**: Active feedback collection

### Advanced Analytics
- **Stability Scoring**: Based on 7-day pod history
- **Resource Pressure**: Cluster-wide health analysis
- **Failure Rate Prediction**: Historical pod analysis
- **ML Model Performance**: Continuous monitoring and updates

## 🛠️ Development

### Project Structure
```
ai-scheduler/
├── go/                    # Go backend
│   ├── cmd/main.go       # Entry point
│   ├── internal/         # Core logic
│   │   ├── api/         # HTTP routes
│   │   ├── collector/   # Metrics collection
│   │   ├── scheduler/   # AI scheduler logic
│   │   └── types/       # Data structures
│   └── config/          # Configuration
├── python/               # Python AI
│   ├── api/app.py       # Flask API
│   ├── data/processor.py # Data processing
│   ├── models/          # ML models
│   └── config/          # Configuration
├── scripts/             # Test scripts
├── docker-compose.yml   # Container orchestration
└── README.md           # This file
```

### Building from Source
```bash
# Build Go backend
cd go
go build -o main cmd/main.go

# Build Python AI
cd ../python
pip install -r requirements.txt
python api/app.py
```

## 🔍 Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check if ports are in use
   lsof -i :8080
   lsof -i :5000
   
   # Kill processes if needed
   sudo kill -9 <PID>
   ```

2. **Docker Container Issues**
   ```bash
   # Check container logs
   docker-compose logs go-backend
   docker-compose logs python-ai
   
   # Restart services
   docker-compose restart
   ```

3. **Kubernetes Connection Issues**
   ```bash
   # Start Minikube if needed
   minikube start
   
   # Check Kubernetes connection
   kubectl get nodes
   ```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Kubernetes client-go library
- Scikit-learn for ML models
- Flask for Python API
- Gin for Go API
- Docker for containerization

---

**AI-Enhanced Kubernetes Scheduler** - Making intelligent pod placement decisions with machine learning and historical data analysis. 