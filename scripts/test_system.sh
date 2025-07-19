#!/bin/bash

# AI Scheduler System Test Script
# Tests both Go Backend and Python AI APIs

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GO_BACKEND_URL="http://localhost:8080"
PYTHON_AI_URL="http://localhost:5000"
TIMEOUT=10

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "PASS")
            echo -e "${GREEN}✅ PASS${NC}: $message"
            ;;
        "FAIL")
            echo -e "${RED}❌ FAIL${NC}: $message"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  INFO${NC}: $message"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠️  WARN${NC}: $message"
            ;;
    esac
}

# Function to test API endpoint
test_endpoint() {
    local name=$1
    local method=$2
    local url=$3
    local data=$4
    local expected_status=$5
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    print_status "INFO" "Testing $name..."
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "%{http_code}" -X $method -H "Content-Type: application/json" -d "$data" "$url" 2>/dev/null)
    else
        response=$(curl -s -w "%{http_code}" -X $method "$url" 2>/dev/null)
    fi
    
    http_code="${response: -3}"
    response_body="${response%???}"
    
    if [ "$http_code" = "$expected_status" ]; then
        print_status "PASS" "$name - HTTP $http_code"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo "$response_body" | jq . 2>/dev/null || echo "$response_body"
    else
        print_status "FAIL" "$name - Expected HTTP $expected_status, got HTTP $http_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo "Response: $response_body"
    fi
    
    echo ""
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_status "INFO" "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url/health" > /dev/null 2>&1; then
            print_status "PASS" "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_status "FAIL" "$service_name failed to start after $max_attempts attempts"
    return 1
}

# Main test function
run_tests() {
    echo -e "${BLUE}🚀 AI Scheduler System Tests${NC}"
    echo "=================================="
    echo ""
    
    # Test 1: Go Backend Health Check
    print_status "INFO" "Testing Go Backend..."
    test_endpoint "Go Backend Health" "GET" "$GO_BACKEND_URL/health" "" "200"
    
    # Test 2: Go Backend Metrics
    test_endpoint "Go Backend Metrics" "GET" "$GO_BACKEND_URL/api/v1/metrics" "" "200"
    
    # Test 3: Python AI Health Check
    print_status "INFO" "Testing Python AI..."
    test_endpoint "Python AI Health" "GET" "$PYTHON_AI_URL/health" "" "200"
    
    # Test 4: Python AI Data Summary
    test_endpoint "Python AI Data Summary" "GET" "$PYTHON_AI_URL/data/summary" "" "200"
    
    # Test 5: Python AI Model Info
    test_endpoint "Python AI Model Info" "GET" "$PYTHON_AI_URL/model/info" "" "200"
    
    # Test 6: Python AI Performance
    test_endpoint "Python AI Performance" "GET" "$PYTHON_AI_URL/performance" "" "200"
    
    # Test 7: Python AI Prediction
    local prediction_data='{
        "pod_name": "test-pod-1",
        "pod_namespace": "default",
        "pod_spec": {
            "containers": [{
                "name": "app",
                "resources": {
                    "requests": {
                        "cpu": "100m",
                        "memory": "128Mi"
                    }
                }
            }]
        }
    }'
    test_endpoint "Python AI Prediction" "POST" "$PYTHON_AI_URL/predict" "$prediction_data" "200"
    
    # Test 8: Python AI Feedback
    local feedback_data='{
        "prediction_result": {
            "predicted_node": "minikube",
            "confidence": 0.95,
            "algorithm": "ml_prediction",
            "ai_features": {
                "pod_requirements": {"cpu_request": 0.1, "memory_request": 128.0},
                "cluster_state": {"total_nodes": 1, "ready_nodes": 1}
            }
        },
        "actual_node": "minikube",
        "success": true,
        "pod_status": "Running"
    }'
    test_endpoint "Python AI Feedback" "POST" "$PYTHON_AI_URL/feedback" "$feedback_data" "200"
    
    # Test 9: Python AI Recent Feedback
    test_endpoint "Python AI Recent Feedback" "GET" "$PYTHON_AI_URL/feedback/recent?limit=5" "" "200"
    
    # Test 10: Multiple Predictions
    print_status "INFO" "Testing multiple predictions..."
    for i in {1..3}; do
        local multi_prediction_data="{
            \"pod_name\": \"test-pod-$i\",
            \"pod_namespace\": \"default\",
            \"pod_spec\": {
                \"containers\": [{
                    \"name\": \"app\",
                    \"resources\": {
                        \"requests\": {
                            \"cpu\": \"${i}00m\",
                            \"memory\": \"${i}28Mi\"
                        }
                    }
                }]
            }
        }"
        test_endpoint "Python AI Prediction $i" "POST" "$PYTHON_AI_URL/predict" "$multi_prediction_data" "200"
    done
    
    # Test 11: Performance after predictions
    test_endpoint "Python AI Performance After Predictions" "GET" "$PYTHON_AI_URL/performance" "" "200"
}

# Function to test Docker containers
test_docker_containers() {
    echo -e "${BLUE}🐳 Docker Container Tests${NC}"
    echo "=========================="
    echo ""
    
    # Check if containers are running
    if docker ps --format "table {{.Names}}" | grep -q "ai-scheduler-go-backend"; then
        print_status "PASS" "Go Backend container is running"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        print_status "FAIL" "Go Backend container is not running"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if docker ps --format "table {{.Names}}" | grep -q "ai-scheduler-python-ai"; then
        print_status "PASS" "Python AI container is running"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        print_status "FAIL" "Python AI container is not running"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    # Check container health
    if docker inspect ai-scheduler-go-backend --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
        print_status "PASS" "Go Backend container is healthy"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        print_status "WARN" "Go Backend container health check failed"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if docker inspect ai-scheduler-python-ai --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
        print_status "PASS" "Python AI container is healthy"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        print_status "WARN" "Python AI container health check failed"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

# Function to show test summary
show_summary() {
    echo -e "${BLUE}📊 Test Summary${NC}"
    echo "================"
    echo ""
    echo -e "Total Tests: ${TOTAL_TESTS}"
    echo -e "Passed: ${GREEN}${PASSED_TESTS}${NC}"
    echo -e "Failed: ${RED}${FAILED_TESTS}${NC}"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        echo ""
        echo -e "${GREEN}🎉 All tests passed! System is working correctly.${NC}"
        exit 0
    else
        echo ""
        echo -e "${RED}❌ Some tests failed. Please check the system.${NC}"
        exit 1
    fi
}

# Main execution
main() {
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        print_status "FAIL" "jq is required but not installed. Please install jq first."
        exit 1
    fi
    
    # Check if curl is installed
    if ! command -v curl &> /dev/null; then
        print_status "FAIL" "curl is required but not installed. Please install curl first."
        exit 1
    fi
    
    # Wait for services to be ready
    if ! wait_for_service "$GO_BACKEND_URL" "Go Backend"; then
        exit 1
    fi
    
    if ! wait_for_service "$PYTHON_AI_URL" "Python AI"; then
        exit 1
    fi
    
    echo ""
    
    # Run API tests
    run_tests
    
    # Run Docker tests if running in Docker
    if [ -f /.dockerenv ] || docker ps &> /dev/null; then
        echo ""
        test_docker_containers
    fi
    
    # Show summary
    echo ""
    show_summary
}

# Run main function
main "$@" 