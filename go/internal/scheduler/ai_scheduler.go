package scheduler

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"ai-scheduler/internal/types"

	"bytes"

	"github.com/sirupsen/logrus"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// NodeScore node skor bilgisi
type NodeScore struct {
	NodeName string  `json:"node_name"`
	Score    float64 `json:"score"`
	Reason   string  `json:"reason"`
}

// Collector interface'i tanımla
// Sadece gerekli metotları içersin (ör: GetMetricsChannel)
type Collector interface {
	GetMetricsChannel() <-chan interface{}
	GetPodCache() *types.PodMetricsCache
}

// AIScheduler AI tabanlı scheduler
type AIScheduler struct {
	k8sClient     *types.K8sClient
	metricsClient *types.MetricsClient
	collector     Collector
	aiAPI         string
	config        *types.SchedulerConfig
	podCache      *types.PodMetricsCache
}

// NewAIScheduler yeni AI scheduler oluşturur
func NewAIScheduler(k8sClient *types.K8sClient, collector Collector, schedulerConfig *types.SchedulerConfig) *AIScheduler {
	metricsClient, err := types.NewMetricsClient(k8sClient)
	if err != nil {
		logrus.Warnf("Metrics client oluşturulamadı, placeholder değerler kullanılacak: %v", err)
	}

	// Collector'dan PodMetricsCache'i al
	podCache := collector.GetPodCache()

	return &AIScheduler{
		k8sClient:     k8sClient,
		metricsClient: metricsClient,
		collector:     collector,
		aiAPI:         schedulerConfig.AIAPIURL,
		config:        schedulerConfig,
		podCache:      podCache,
	}
}

// Start AI scheduler'ı başlatır
func (as *AIScheduler) Start(ctx context.Context) {
	logrus.Info("AI Scheduler başlatılıyor...")

	// Metrik dinleyicisi
	go as.metricsListener(ctx)
}

// metricsListener metrikleri dinler ve AI modelini günceller
func (as *AIScheduler) metricsListener(ctx context.Context) {
	metricsChan := as.collector.GetMetricsChannel()

	for {
		select {
		case <-ctx.Done():
			return
		case metric := <-metricsChan:
			// Metrikleri AI modeline gönder
			as.sendMetricToAI(metric)
		}
	}
}

// sendMetricToAI metriği AI modeline gönderir
func (as *AIScheduler) sendMetricToAI(metric interface{}) {
	_, err := json.Marshal(metric)
	if err != nil {
		logrus.Errorf("Metrik JSON'a çevrilemedi: %v", err)
		return
	}

	resp, err := http.Post(as.aiAPI+"/metrics", "application/json", nil)
	if err != nil {
		logrus.Errorf("AI API'ye metrik gönderilemedi: %v", err)
		return
	}
	defer resp.Body.Close()
}

// PredictBestNode en iyi node'u tahmin eder
func (as *AIScheduler) PredictBestNode(podName, namespace string) (*NodeScore, error) {
	// Pod bilgilerini al
	_, err := as.k8sClient.GetClientset().CoreV1().Pods(namespace).Get(context.Background(), podName, metav1.GetOptions{})
	if err != nil {
		return nil, fmt.Errorf("pod bulunamadı: %v", err)
	}

	// Node listesini al
	nodes, err := as.k8sClient.GetClientset().CoreV1().Nodes().List(context.Background(), metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("node listesi alınamadı: %v", err)
	}

	// Her node için skor hesapla
	var bestNode *NodeScore
	bestScore := -1.0

	for _, node := range nodes.Items {
		score, reason := as.calculateNodeScore(&node)

		if score > bestScore {
			bestScore = score
			bestNode = &NodeScore{
				NodeName: node.Name,
				Score:    score,
				Reason:   reason,
			}
		}
	}

	return bestNode, nil
}

// calculateNodeScore node skorunu hesaplar
func (as *AIScheduler) calculateNodeScore(node *corev1.Node) (float64, string) {
	score := 0.0
	reasons := []string{}

	// CPU kullanımı (lineer skorlama)
	cpu, cpuExists := node.Status.Allocatable["cpu"]
	if cpuExists && !cpu.IsZero() {
		cpuCapacity := float64(cpu.MilliValue()) / 1000.0

		// Gerçek CPU kullanımını al
		var cpuUsage float64
		if as.metricsClient != nil {
			usage, _, err := as.metricsClient.GetNodeMetrics(node.Name)
			if err != nil {
				logrus.Warnf("Node %s için CPU kullanımı alınamadı: %v", node.Name, err)
				cpuUsage = 0.0 // Fallback
			} else {
				cpuUsage = usage
			}
		} else {
			cpuUsage = 0.0 // Fallback
		}

		if cpuCapacity > 0 {
			cpuPercent := (cpuUsage / cpuCapacity) * 100
			cpuScore := as.config.Scoring.CPUWeight * (1 - cpuPercent/100)
			if cpuScore < 0 {
				cpuScore = 0
			}
			score += cpuScore
			reasons = append(reasons, fmt.Sprintf("CPU skoru: %.1f (kullanım: %.2f/%.2f)", cpuScore, cpuUsage, cpuCapacity))
		}
	}

	// Memory kullanımı (lineer skorlama)
	memory, memExists := node.Status.Allocatable["memory"]
	if memExists && !memory.IsZero() {
		memCapacity := float64(memory.Value()) / (1024 * 1024 * 1024) // GB

		// Gerçek Memory kullanımını al
		var memUsage float64
		if as.metricsClient != nil {
			_, usage, err := as.metricsClient.GetNodeMetrics(node.Name)
			if err != nil {
				logrus.Warnf("Node %s için Memory kullanımı alınamadı: %v", node.Name, err)
				memUsage = 0.0 // Fallback
			} else {
				memUsage = usage
			}
		} else {
			memUsage = 0.0 // Fallback
		}

		if memCapacity > 0 {
			memPercent := (memUsage / memCapacity) * 100
			memScore := as.config.Scoring.MemoryWeight * (1 - memPercent/100)
			if memScore < 0 {
				memScore = 0
			}
			score += memScore
			reasons = append(reasons, fmt.Sprintf("Memory skoru: %.1f (kullanım: %.2f/%.2f GB)", memScore, memUsage, memCapacity))
		}
	}

	// Node Ready durumu
	ready := false
	if node.Status.Conditions != nil {
		for _, condition := range node.Status.Conditions {
			if condition.Type == corev1.NodeReady && condition.Status == corev1.ConditionTrue {
				score += as.config.Scoring.NodeReadyWeight
				reasons = append(reasons, "Node hazır")
				ready = true
				break
			}
		}
	}
	if !ready {
		reasons = append(reasons, "Node hazır değil")
	}

	// Taints kontrolü
	if len(node.Spec.Taints) == 0 {
		score += as.config.Scoring.TaintWeight
		reasons = append(reasons, "Taint yok")
	} else {
		reasons = append(reasons, "Taint var")
	}

	// PodMetrics analizi (gelişmiş)
	podAnalysis := as.analyzePodMetrics(node.Name)
	score += podAnalysis.Score
	reasons = append(reasons, podAnalysis.Reasons...)

	reason := fmt.Sprintf("Toplam skor: %.2f - %s", score, reasons)
	return score, reason
}

// analyzePodMetrics PodMetrics'ten node analizi yapar
func (as *AIScheduler) analyzePodMetrics(nodeName string) PodAnalysisResult {
	// Son 24 saatlik analiz
	analysis := as.podCache.GetNodeAnalysis(nodeName, 24*time.Hour)

	score := 0.0
	var reasons []string

	// Kararlılık skoru (0-1 arası)
	stabilityScore := analysis.StabilityScore
	if stabilityScore > 0.8 {
		score += as.config.Scoring.FailedPodsWeight
		reasons = append(reasons, "Yüksek kararlılık")
	} else if stabilityScore > 0.6 {
		score += as.config.Scoring.FailedPodsWeight / 2
		reasons = append(reasons, "Orta kararlılık")
	} else {
		reasons = append(reasons, "Düşük kararlılık")
	}

	// Başarısızlık oranı
	failureRate := analysis.FailureRate
	if failureRate < 0.05 {
		score += as.config.Scoring.FailedPodsWeight
		reasons = append(reasons, "Düşük başarısızlık oranı")
	} else if failureRate < 0.1 {
		score += as.config.Scoring.FailedPodsWeight / 2
		reasons = append(reasons, fmt.Sprintf("Orta başarısızlık oranı: %.2f", failureRate))
	} else {
		score -= as.config.Scoring.FailedPodsWeight
		reasons = append(reasons, fmt.Sprintf("Yüksek başarısızlık oranı: %.2f", failureRate))
	}

	// Restart oranı
	avgRestart := analysis.AverageRestartCount
	if avgRestart <= 1.0 {
		score += as.config.Scoring.RestartWeight
		reasons = append(reasons, "Düşük restart oranı")
	} else if avgRestart <= 2.0 {
		reasons = append(reasons, fmt.Sprintf("Orta restart oranı: %.2f", avgRestart))
	} else {
		score -= as.config.Scoring.RestartWeight
		reasons = append(reasons, fmt.Sprintf("Yüksek restart oranı: %.2f", avgRestart))
	}

	// Pod yaşam süresi
	avgLifetime := analysis.AverageLifetime
	if avgLifetime > 24*time.Hour {
		score += 10.0
		reasons = append(reasons, "Uzun pod yaşam süresi")
	} else if avgLifetime > 1*time.Hour {
		reasons = append(reasons, "Normal pod yaşam süresi")
	} else {
		score -= 10.0
		reasons = append(reasons, "Kısa pod yaşam süresi")
	}

	return PodAnalysisResult{
		Score:   score,
		Reasons: reasons,
	}
}

// PodAnalysisResult pod analiz sonucu
type PodAnalysisResult struct {
	Score   float64
	Reasons []string
}

// extractFeaturesForAI node için AI modeli için features çıkarır
func (as *AIScheduler) extractFeaturesForAI(nodeName string) map[string]interface{} {
	// Node analizi
	nodeAnalysis := as.podCache.GetNodeAnalysis(nodeName, 24*time.Hour)

	// CPU ve Memory kullanımı
	var cpuUsage, memUsage float64
	if as.metricsClient != nil {
		cpu, mem, err := as.metricsClient.GetNodeMetrics(nodeName)
		if err == nil {
			cpuUsage = cpu
			memUsage = mem
		}
	}

	// Node kapasitesi
	node, err := as.k8sClient.GetClientset().CoreV1().Nodes().Get(context.Background(), nodeName, metav1.GetOptions{})
	var cpuCapacity, memCapacity float64
	if err == nil {
		if cpu := node.Status.Allocatable["cpu"]; !cpu.IsZero() {
			cpuCapacity = float64(cpu.MilliValue()) / 1000.0
		}
		if memory := node.Status.Allocatable["memory"]; !memory.IsZero() {
			memCapacity = float64(memory.Value()) / (1024 * 1024 * 1024) // GB
		}
	}

	// CPU ve Memory oranları
	cpuRatio := 0.0
	memRatio := 0.0
	if cpuCapacity > 0 {
		cpuRatio = cpuUsage / cpuCapacity
	}
	if memCapacity > 0 {
		memRatio = memUsage / memCapacity
	}

	// Pod yoğunluğu
	podDensity := 0.0
	if nodeAnalysis.TotalPods > 0 {
		podDensity = float64(nodeAnalysis.TotalPods) / 10.0 // Normalize
	}

	// Trend analizi (son 7 gün)
	weekAnalysis := as.podCache.GetNodeAnalysis(nodeName, 7*24*time.Hour)
	trendScore := (weekAnalysis.StabilityScore - nodeAnalysis.StabilityScore) * 10 // Trend

	// Risk faktörleri
	riskFactors := []string{}
	if nodeAnalysis.FailureRate > 0.1 {
		riskFactors = append(riskFactors, "high_failure_rate")
	}
	if nodeAnalysis.AverageRestartCount > 2.0 {
		riskFactors = append(riskFactors, "high_restart_rate")
	}
	if cpuRatio > 0.8 {
		riskFactors = append(riskFactors, "high_cpu_usage")
	}
	if memRatio > 0.8 {
		riskFactors = append(riskFactors, "high_memory_usage")
	}

	// Özellik vektörü
	features := map[string]interface{}{
		// Temel metrikler
		"cpu_usage_ratio":        cpuRatio,
		"memory_usage_ratio":     memRatio,
		"pod_count":              nodeAnalysis.TotalPods,
		"failed_pods_ratio":      nodeAnalysis.FailureRate,
		"avg_restart_count":      nodeAnalysis.AverageRestartCount,
		"avg_pod_lifetime_hours": nodeAnalysis.AverageLifetime.Hours(),

		// Türetilen özellikler
		"stability_score": nodeAnalysis.StabilityScore,
		"pod_density":     podDensity,
		"trend_score":     trendScore,
		"success_rate":    1.0 - nodeAnalysis.FailureRate,

		// Risk faktörleri
		"risk_factors": riskFactors,
		"risk_score":   float64(len(riskFactors)) / 4.0, // 0-1 arası

		// Zaman bazlı özellikler
		"hour_of_day": float64(time.Now().Hour()) / 24.0,
		"day_of_week": float64(time.Now().Weekday()) / 7.0,

		// Kapasite bilgileri
		"cpu_capacity":        cpuCapacity,
		"memory_capacity_gb":  memCapacity,
		"available_cpu":       cpuCapacity - cpuUsage,
		"available_memory_gb": memCapacity - memUsage,
	}

	return features
}

// getAIAnalysis Python AI'dan analiz alır
func (as *AIScheduler) getAIAnalysis(nodeName string) (map[string]interface{}, error) {
	// Features çıkar
	features := as.extractFeaturesForAI(nodeName)

	// Python AI'ya gönder
	requestBody := map[string]interface{}{
		"node_name": nodeName,
		"features":  features,
		"timestamp": time.Now().Unix(),
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return nil, fmt.Errorf("request JSON'a çevrilemedi: %v", err)
	}

	// HTTP request
	resp, err := http.Post(as.aiAPI+"/analyze", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("AI API'ye istek gönderilemedi: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("AI API hata döndürdü: %d", resp.StatusCode)
	}

	// Response parse et
	var aiResponse map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&aiResponse); err != nil {
		return nil, fmt.Errorf("AI response parse edilemedi: %v", err)
	}

	return aiResponse, nil
}

// makeFinalDecision AI analizi ve Go algoritmasını birleştirir
func (as *AIScheduler) makeFinalDecision(nodeName string, goScore float64) (float64, string) {
	// AI analizi al
	aiAnalysis, err := as.getAIAnalysis(nodeName)
	if err != nil {
		logrus.Warnf("AI analizi alınamadı, sadece Go skoru kullanılacak: %v", err)
		return goScore, "Sadece Go algoritması kullanıldı"
	}

	// AI skorunu al
	aiScore, ok := aiAnalysis["score"].(float64)
	if !ok {
		logrus.Warnf("AI skoru alınamadı, sadece Go skoru kullanılacak")
		return goScore, "Sadece Go algoritması kullanıldı"
	}

	// AI güvenilirlik skoru
	confidence, ok := aiAnalysis["confidence"].(float64)
	if !ok {
		confidence = 0.5 // Default güvenilirlik
	}

	// Final skor hesapla (AI %70, Go %30)
	finalScore := (aiScore * confidence * 0.7) + (goScore * 0.3)

	reason := fmt.Sprintf("Final skor: %.2f (AI: %.2f, Go: %.2f, Confidence: %.2f)",
		finalScore, aiScore, goScore, confidence)

	return finalScore, reason
}
