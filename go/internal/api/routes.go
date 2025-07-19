package api

import (
	"net/http"

	"ai-scheduler/internal/collector"
	"ai-scheduler/internal/scheduler"

	"github.com/gin-gonic/gin"
)

// SetupRoutes API route'larını ayarlar
func SetupRoutes(router *gin.Engine, aiScheduler *scheduler.AIScheduler, collector *collector.DataCollector) {
	// Health check
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "healthy",
			"service": "ai-scheduler",
		})
	})

	// API v1 group
	v1 := router.Group("/api/v1")
	{
		// Scheduler endpoints
		v1.POST("/predict", predictNode(aiScheduler))
		v1.GET("/nodes", getNodes(aiScheduler))
		v1.GET("/metrics", getMetrics(collector))

		// AI model endpoints
		v1.POST("/model/train", trainModel(aiScheduler))
		v1.GET("/model/status", getModelStatus(aiScheduler))
	}
}

// predictNode node tahmini yapar
func predictNode(aiScheduler *scheduler.AIScheduler) gin.HandlerFunc {
	return func(c *gin.Context) {
		var request struct {
			PodName   string `json:"pod_name" binding:"required"`
			Namespace string `json:"namespace" binding:"required"`
		}

		if err := c.ShouldBindJSON(&request); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		nodeScore, err := aiScheduler.PredictBestNode(request.PodName, request.Namespace)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"prediction": nodeScore,
		})
	}
}

// getNodes node listesini döndürür
func getNodes(aiScheduler *scheduler.AIScheduler) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Node listesi implementasyonu
		c.JSON(http.StatusOK, gin.H{
			"nodes": []string{},
		})
	}
}

// getMetrics metrikleri döndürür
func getMetrics(collector *collector.DataCollector) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Mock node data for testing
		nodes := []gin.H{
			{
				"name":         "minikube",
				"cpu_usage":    45.2,
				"memory_usage": 62.8,
				"ready":        true,
				"taints":       []string{},
			},
		}

		c.JSON(http.StatusOK, gin.H{
			"nodes": nodes,
		})
	}
}

// trainModel AI modelini eğitir
func trainModel(aiScheduler *scheduler.AIScheduler) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Model eğitimi implementasyonu
		c.JSON(http.StatusOK, gin.H{
			"status": "training_started",
		})
	}
}

// getModelStatus model durumunu döndürür
func getModelStatus(aiScheduler *scheduler.AIScheduler) gin.HandlerFunc {
	return func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "ready",
			"version": "1.0.0",
		})
	}
}
