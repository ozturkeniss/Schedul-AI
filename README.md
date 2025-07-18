# AI-Powered Kubernetes Scheduler

Bu proje, Kubernetes scheduler'ının pod yerleştirme mekanizmasını AI ile geliştirmeyi amaçlamaktadır. Geleneksel taints and tolerations yaklaşımının yanı sıra, çeşitli verilerden öğrenerek daha akıllı yerleştirme kararları verir.

## Özellikler

- **AI Tabanlı Karar Verme**: Pod ölüm oranları, kaynak kullanımı, performans metrikleri gibi verilerden öğrenme
- **Gerçek Zamanlı Analiz**: Kubernetes API'den canlı veri toplama
- **Çoklu Faktör Analizi**: CPU, memory, network, disk kullanımı ve pod geçmişi
- **Otomatik Model Güncelleme**: Yeni veriler geldikçe model sürekli öğrenir

## Proje Yapısı

```
ai-scheduler/
├── go/                    # Go backend (Kubernetes API entegrasyonu)
│   ├── cmd/              # Ana uygulama
│   ├── internal/         # İç modüller
│   └── pkg/              # Dışa açık paketler
├── python/               # Python AI/ML bileşenleri
│   ├── models/           # ML modelleri
│   ├── data/             # Veri işleme
│   └── api/              # Python API
├── k8s/                  # Kubernetes manifestleri
└── docs/                 # Dokümantasyon
```

## Teknolojiler

- **Backend**: Go (Kubernetes client-go)
- **AI/ML**: Python (scikit-learn, TensorFlow/PyTorch)
- **Veri Tabanı**: PostgreSQL/Redis
- **API**: gRPC/REST
- **Monitoring**: Prometheus, Grafana

## Kurulum

```bash
# Go dependencies
cd go && go mod init ai-scheduler
go get k8s.io/client-go

# Python dependencies
cd python && pip install -r requirements.txt
```

## Kullanım

1. Kubernetes cluster'ında AI scheduler'ı deploy edin
2. Model eğitimi için veri toplamaya başlayın
3. AI tabanlı yerleştirme kararlarını izleyin

## Katkıda Bulunma

Bu proje açık kaynak kodludur. Katkılarınızı bekliyoruz! 