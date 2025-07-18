package types

import "time"

// NodeMetrics node metrikleri
type NodeMetrics struct {
	NodeName    string    `json:"node_name"`
	CPUUsage    float64   `json:"cpu_usage"`
	MemoryUsage float64   `json:"memory_usage"`
	PodCount    int       `json:"pod_count"`
	FailedPods  int       `json:"failed_pods"`
	Timestamp   time.Time `json:"timestamp"`
}

// PodMetrics pod metrikleri
type PodMetrics struct {
	PodName      string    `json:"pod_name"`
	NodeName     string    `json:"node_name"`
	Namespace    string    `json:"namespace"`
	Status       string    `json:"status"`
	RestartCount int       `json:"restart_count"`
	CreatedAt    time.Time `json:"created_at"`
	Timestamp    time.Time `json:"timestamp"`
}
