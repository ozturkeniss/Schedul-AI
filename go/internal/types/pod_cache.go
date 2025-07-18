package types

import (
	"sync"
	"time"
)

// PodMetricsCache PodMetrics için cache sistemi
type PodMetricsCache struct {
	nodePodHistory map[string][]PodMetrics
	failureRates   map[string]float64
	restartRates   map[string]float64
	lastUpdated    map[string]time.Time
	mutex          sync.RWMutex
}

// NewPodMetricsCache yeni cache oluşturur
func NewPodMetricsCache() *PodMetricsCache {
	return &PodMetricsCache{
		nodePodHistory: make(map[string][]PodMetrics),
		failureRates:   make(map[string]float64),
		restartRates:   make(map[string]float64),
		lastUpdated:    make(map[string]time.Time),
	}
}

// UpdateCache cache'i günceller
func (pmc *PodMetricsCache) UpdateCache(podMetrics PodMetrics) {
	pmc.mutex.Lock()
	defer pmc.mutex.Unlock()

	nodeName := podMetrics.NodeName
	pmc.nodePodHistory[nodeName] = append(pmc.nodePodHistory[nodeName], podMetrics)

	// Eski verileri temizle (son 7 gün)
	pmc.cleanOldData(nodeName, 7*24*time.Hour)

	// İstatistikleri güncelle
	pmc.updateStatistics(nodeName)
}

// GetNodeMetrics node için metrikleri döndürür
func (pmc *PodMetricsCache) GetNodeMetrics(nodeName string) []PodMetrics {
	pmc.mutex.RLock()
	defer pmc.mutex.RUnlock()

	return pmc.nodePodHistory[nodeName]
}

// GetFailureRate node'un başarısızlık oranını döndürür
func (pmc *PodMetricsCache) GetFailureRate(nodeName string) float64 {
	pmc.mutex.RLock()
	defer pmc.mutex.RUnlock()

	return pmc.failureRates[nodeName]
}

// GetRestartRate node'un restart oranını döndürür
func (pmc *PodMetricsCache) GetRestartRate(nodeName string) float64 {
	pmc.mutex.RLock()
	defer pmc.mutex.RUnlock()

	return pmc.restartRates[nodeName]
}

// cleanOldData eski verileri temizler
func (pmc *PodMetricsCache) cleanOldData(nodeName string, maxAge time.Duration) {
	cutoffTime := time.Now().Add(-maxAge)
	var filteredMetrics []PodMetrics

	for _, metric := range pmc.nodePodHistory[nodeName] {
		if metric.Timestamp.After(cutoffTime) {
			filteredMetrics = append(filteredMetrics, metric)
		}
	}

	pmc.nodePodHistory[nodeName] = filteredMetrics
}

// updateStatistics node istatistiklerini günceller
func (pmc *PodMetricsCache) updateStatistics(nodeName string) {
	metrics := pmc.nodePodHistory[nodeName]
	if len(metrics) == 0 {
		return
	}

	// Başarısızlık oranı hesapla
	failedPods := 0
	totalRestarts := 0
	for _, metric := range metrics {
		if metric.Status == "Failed" {
			failedPods++
		}
		totalRestarts += metric.RestartCount
	}

	failureRate := float64(failedPods) / float64(len(metrics))
	restartRate := float64(totalRestarts) / float64(len(metrics))

	pmc.failureRates[nodeName] = failureRate
	pmc.restartRates[nodeName] = restartRate
	pmc.lastUpdated[nodeName] = time.Now()
}

// GetNodeAnalysis node analizi döndürür
func (pmc *PodMetricsCache) GetNodeAnalysis(nodeName string, timeWindow time.Duration) NodeAnalysis {
	pmc.mutex.RLock()
	defer pmc.mutex.RUnlock()

	metrics := pmc.nodePodHistory[nodeName]
	cutoffTime := time.Now().Add(-timeWindow)

	var recentMetrics []PodMetrics
	for _, metric := range metrics {
		if metric.Timestamp.After(cutoffTime) {
			recentMetrics = append(recentMetrics, metric)
		}
	}

	return calculateNodeAnalysis(recentMetrics)
}

// NodeAnalysis node analiz sonucu
type NodeAnalysis struct {
	NodeName            string
	TotalPods           int
	FailedPods          int
	SuccessfulPods      int
	FailureRate         float64
	AverageRestartCount float64
	AverageLifetime     time.Duration
	StabilityScore      float64
	Recommendations     []string
}

// calculateNodeAnalysis node analizi hesaplar
func calculateNodeAnalysis(metrics []PodMetrics) NodeAnalysis {
	if len(metrics) == 0 {
		return NodeAnalysis{}
	}

	failedPods := 0
	totalRestarts := 0
	var totalLifetime time.Duration

	for _, metric := range metrics {
		if metric.Status == "Failed" {
			failedPods++
		}
		totalRestarts += metric.RestartCount
		totalLifetime += time.Since(metric.CreatedAt)
	}

	failureRate := float64(failedPods) / float64(len(metrics))
	avgRestartCount := float64(totalRestarts) / float64(len(metrics))
	avgLifetime := totalLifetime / time.Duration(len(metrics))

	// Kararlılık skoru (0-1 arası)
	stabilityScore := 1.0 - failureRate - (avgRestartCount * 0.1)

	// Öneriler
	var recommendations []string
	if failureRate > 0.1 {
		recommendations = append(recommendations, "Yüksek başarısızlık oranı")
	}
	if avgRestartCount > 2.0 {
		recommendations = append(recommendations, "Yüksek restart oranı")
	}
	if stabilityScore < 0.7 {
		recommendations = append(recommendations, "Düşük kararlılık")
	}

	return NodeAnalysis{
		NodeName:            metrics[0].NodeName,
		TotalPods:           len(metrics),
		FailedPods:          failedPods,
		SuccessfulPods:      len(metrics) - failedPods,
		FailureRate:         failureRate,
		AverageRestartCount: avgRestartCount,
		AverageLifetime:     avgLifetime,
		StabilityScore:      stabilityScore,
		Recommendations:     recommendations,
	}
}
