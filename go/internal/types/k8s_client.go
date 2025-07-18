package types

import (
	"os"
	"path/filepath"

	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

// K8sClient Kubernetes client wrapper
type K8sClient struct {
	Clientset *kubernetes.Clientset
	Config    *rest.Config
}

// NewK8sClient yeni Kubernetes client oluşturur
func NewK8sClient() (*K8sClient, error) {
	var config *rest.Config
	var err error

	// In-cluster config kontrolü
	if _, err := os.Stat("/var/run/secrets/kubernetes.io/serviceaccount/token"); err == nil {
		config, err = rest.InClusterConfig()
	} else {
		// Kubeconfig dosyasından config yükleme
		kubeconfig := filepath.Join(os.Getenv("HOME"), ".kube", "config")
		config, err = clientcmd.BuildConfigFromFlags("", kubeconfig)
	}

	if err != nil {
		return nil, err
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, err
	}

	return &K8sClient{
		Clientset: clientset,
		Config:    config,
	}, nil
}

// GetClientset clientset'i döndürür
func (k *K8sClient) GetClientset() *kubernetes.Clientset {
	return k.Clientset
}
