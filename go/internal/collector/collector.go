package collector

import (
	"context"
	"time"

	"ai-scheduler/internal/types"

	"github.com/sirupsen/logrus"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// DataCollector veri toplayıcı
type DataCollector struct {
	k8sClient     *types.K8sClient
	metricsClient *types.MetricsClient
	config        *types.MetricsConfig
	podCache      *types.PodMetricsCache
	metrics       chan interface{}
}

// NewDataCollector yeni veri toplayıcı oluşturur
func NewDataCollector(k8sClient *types.K8sClient, metricsConfig *types.MetricsConfig) *DataCollector {
	metricsClient, err := types.NewMetricsClient(k8sClient)
	if err != nil {
		logrus.Warnf("Metrics client oluşturulamadı, placeholder değerler kullanılacak: %v", err)
	}

	return &DataCollector{
		k8sClient:     k8sClient,
		metricsClient: metricsClient,
		config:        metricsConfig,
		podCache:      types.NewPodMetricsCache(),
		metrics:       make(chan interface{}, 1000),
	}
}

// Start veri toplamayı başlatır
func (dc *DataCollector) Start(ctx context.Context) {
	interval := dc.config.CollectionInterval
	if interval == 0 {
		interval = 30 * time.Second // Default değer
	}

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			dc.collectNodeMetrics()
			dc.collectPodMetrics()
		}
	}
}

// collectNodeMetrics node metriklerini toplar
func (dc *DataCollector) collectNodeMetrics() {
	nodes, err := dc.k8sClient.GetClientset().CoreV1().Nodes().List(context.Background(), metav1.ListOptions{})
	if err != nil {
		logrus.Errorf("Node listesi alınamadı: %v", err)
		return
	}

	for _, node := range nodes.Items {
		// Node metrikleri hesaplama
		metrics := types.NodeMetrics{
			NodeName:  node.Name,
			PodCount:  len(node.Status.Allocatable),
			Timestamp: time.Now(),
		}

		// Gerçek CPU ve Memory kullanımını al
		if dc.metricsClient != nil {
			cpuUsage, memUsage, err := dc.metricsClient.GetNodeMetrics(node.Name)
			if err != nil {
				logrus.Warnf("Node %s için metrikler alınamadı: %v", node.Name, err)
				// Fallback: placeholder değerler
				metrics.CPUUsage = 0.0
				metrics.MemoryUsage = 0.0
			} else {
				metrics.CPUUsage = cpuUsage
				metrics.MemoryUsage = memUsage
			}
		} else {
			// Metrics client yoksa placeholder değerler
			metrics.CPUUsage = 0.0
			metrics.MemoryUsage = 0.0
		}

		dc.metrics <- metrics
	}
}

// collectPodMetrics pod metriklerini toplar
func (dc *DataCollector) collectPodMetrics() {
	pods, err := dc.k8sClient.GetClientset().CoreV1().Pods("").List(context.Background(), metav1.ListOptions{})
	if err != nil {
		logrus.Errorf("Pod listesi alınamadı: %v", err)
		return
	}

	for _, pod := range pods.Items {
		restartCount := 0
		for _, container := range pod.Status.ContainerStatuses {
			restartCount += int(container.RestartCount)
		}

		metrics := types.PodMetrics{
			PodName:      pod.Name,
			NodeName:     pod.Spec.NodeName,
			Namespace:    pod.Namespace,
			Status:       string(pod.Status.Phase),
			RestartCount: restartCount,
			CreatedAt:    pod.CreationTimestamp.Time,
			Timestamp:    time.Now(),
		}

		// PodMetrics'i cache'e kaydet
		dc.podCache.UpdateCache(metrics)

		// Metrics channel'a gönder
		dc.metrics <- metrics
	}
}

// GetMetricsChannel metrik kanalını döndürür
func (dc *DataCollector) GetMetricsChannel() <-chan interface{} {
	return dc.metrics
}

// GetPodCache PodMetricsCache'i döndürür
func (dc *DataCollector) GetPodCache() *types.PodMetricsCache {
	return dc.podCache
}
