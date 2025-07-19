package types

import (
	"context"
	"fmt"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	metricsv1beta1 "k8s.io/metrics/pkg/client/clientset/versioned"
)

// MetricsClient Kubernetes metrics API client wrapper
type MetricsClient struct {
	metricsClient *metricsv1beta1.Clientset
}

// NewMetricsClient yeni metrics client oluşturur
func NewMetricsClient(k8sClient *K8sClient) (*MetricsClient, error) {
	// Kubernetes client kontrolü
	if k8sClient == nil || k8sClient.Config == nil {
		return &MetricsClient{
			metricsClient: nil,
		}, nil
	}

	metricsClient, err := metricsv1beta1.NewForConfig(k8sClient.Config)
	if err != nil {
		return nil, fmt.Errorf("metrics client oluşturulamadı: %v", err)
	}

	return &MetricsClient{
		metricsClient: metricsClient,
	}, nil
}

// GetNodeMetrics node'un CPU ve memory kullanımını döndürür
func (mc *MetricsClient) GetNodeMetrics(nodeName string) (float64, float64, error) {
	// Metrics client kontrolü
	if mc == nil || mc.metricsClient == nil {
		return 0.0, 0.0, fmt.Errorf("metrics client kullanılamıyor")
	}

	nodeMetrics, err := mc.metricsClient.MetricsV1beta1().NodeMetricses().Get(context.Background(), nodeName, metav1.GetOptions{})
	if err != nil {
		return 0, 0, fmt.Errorf("node metrics alınamadı: %v", err)
	}

	// CPU kullanımı (cores)
	cpuUsage := float64(nodeMetrics.Usage.Cpu().MilliValue()) / 1000.0

	// Memory kullanımı (bytes)
	memUsageBytes := float64(nodeMetrics.Usage.Memory().Value())
	memUsageGB := memUsageBytes / (1024 * 1024 * 1024)

	return cpuUsage, memUsageGB, nil
}

// GetPodMetrics pod'un CPU ve memory kullanımını döndürür
func (mc *MetricsClient) GetPodMetrics(namespace, podName string) (float64, float64, error) {
	// Metrics client kontrolü
	if mc == nil || mc.metricsClient == nil {
		return 0.0, 0.0, fmt.Errorf("metrics client kullanılamıyor")
	}

	podMetrics, err := mc.metricsClient.MetricsV1beta1().PodMetricses(namespace).Get(context.Background(), podName, metav1.GetOptions{})
	if err != nil {
		return 0, 0, fmt.Errorf("pod metrics alınamadı: %v", err)
	}

	// Pod'un tüm container'larının toplam kullanımı
	var totalCPU, totalMemory float64
	for _, container := range podMetrics.Containers {
		totalCPU += float64(container.Usage.Cpu().MilliValue()) / 1000.0
		totalMemory += float64(container.Usage.Memory().Value()) / (1024 * 1024 * 1024) // GB
	}

	return totalCPU, totalMemory, nil
}

// GetNodeCapacity node'un toplam kapasitesini döndürür
func (mc *MetricsClient) GetNodeCapacity(nodeName string) (float64, float64, error) {
	// Bu bilgi için normal Kubernetes API kullanılır
	// Metrics API sadece kullanım bilgisi verir
	return 0, 0, fmt.Errorf("node capacity için normal k8s API kullanılmalı")
}
