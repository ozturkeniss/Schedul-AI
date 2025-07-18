package types

import "time"

// Config ana konfigürasyon struct'ı
type Config struct {
	Server      ServerConfig      `mapstructure:"server"`
	Kubernetes  KubernetesConfig  `mapstructure:"kubernetes"`
	Metrics     MetricsConfig     `mapstructure:"metrics"`
	Scheduler   SchedulerConfig   `mapstructure:"scheduler"`
	Logging     LoggingConfig     `mapstructure:"logging"`
	Monitoring  MonitoringConfig  `mapstructure:"monitoring"`
	Development DevelopmentConfig `mapstructure:"development"`
}

// ServerConfig server ayarları
type ServerConfig struct {
	Port         int           `mapstructure:"port"`
	Host         string        `mapstructure:"host"`
	ReadTimeout  time.Duration `mapstructure:"read_timeout"`
	WriteTimeout time.Duration `mapstructure:"write_timeout"`
}

// KubernetesConfig Kubernetes ayarları
type KubernetesConfig struct {
	InCluster      bool          `mapstructure:"in_cluster"`
	KubeconfigPath string        `mapstructure:"kubeconfig_path"`
	APITimeout     time.Duration `mapstructure:"api_timeout"`
}

// MetricsConfig metrics ayarları
type MetricsConfig struct {
	CollectionInterval time.Duration `mapstructure:"collection_interval"`
	APITimeout         time.Duration `mapstructure:"api_timeout"`
	EnableFallback     bool          `mapstructure:"enable_fallback"`
}

// SchedulerConfig scheduler ayarları
type SchedulerConfig struct {
	AIAPIURL   string          `mapstructure:"ai_api_url"`
	Scoring    ScoringConfig   `mapstructure:"scoring"`
	Thresholds ThresholdConfig `mapstructure:"thresholds"`
}

// ScoringConfig skorlama ağırlıkları
type ScoringConfig struct {
	CPUWeight        float64 `mapstructure:"cpu_weight"`
	MemoryWeight     float64 `mapstructure:"memory_weight"`
	NodeReadyWeight  float64 `mapstructure:"node_ready_weight"`
	TaintWeight      float64 `mapstructure:"taint_weight"`
	FailedPodsWeight float64 `mapstructure:"failed_pods_weight"`
	RestartWeight    float64 `mapstructure:"restart_weight"`
}

// ThresholdConfig skorlama eşikleri
type ThresholdConfig struct {
	CPUUsageThreshold    float64 `mapstructure:"cpu_usage_threshold"`
	MemoryUsageThreshold float64 `mapstructure:"memory_usage_threshold"`
	FailedPodsThreshold  int     `mapstructure:"failed_pods_threshold"`
	AvgRestartThreshold  float64 `mapstructure:"avg_restart_threshold"`
}

// LoggingConfig logging ayarları
type LoggingConfig struct {
	Level   string `mapstructure:"level"`
	Format  string `mapstructure:"format"`
	File    string `mapstructure:"file"`
	Console bool   `mapstructure:"console"`
}

// MonitoringConfig monitoring ayarları
type MonitoringConfig struct {
	HealthCheck     bool `mapstructure:"health_check"`
	MetricsEndpoint bool `mapstructure:"metrics_endpoint"`
	Prometheus      bool `mapstructure:"prometheus"`
}

// DevelopmentConfig development ayarları
type DevelopmentConfig struct {
	Debug     bool `mapstructure:"debug"`
	HotReload bool `mapstructure:"hot_reload"`
	MockData  bool `mapstructure:"mock_data"`
}
