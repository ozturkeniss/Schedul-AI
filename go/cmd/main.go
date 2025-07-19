package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"ai-scheduler/internal/api"
	"ai-scheduler/internal/collector"
	"ai-scheduler/internal/scheduler"
	"ai-scheduler/internal/types"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
	"github.com/spf13/viper"
)

func main() {
	// Konfigürasyon yükleme
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("./config")
	viper.AutomaticEnv()

	if err := viper.ReadInConfig(); err != nil {
		logrus.Warnf("Config dosyası okunamadı: %v", err)
	}

	// Konfigürasyon struct'ına yükle
	var config types.Config
	if err := viper.Unmarshal(&config); err != nil {
		logrus.Fatalf("Konfigürasyon parse edilemedi: %v", err)
	}

	// Logger ayarları
	setupLogging(&config.Logging)

	// Kubernetes client oluşturma
	k8sClient, err := types.NewK8sClient()
	if err != nil {
		logrus.Fatalf("Kubernetes client oluşturulamadı: %v", err)
	}

	// Kubernetes client kontrolü
	if k8sClient.Clientset == nil {
		logrus.Warn("Kubernetes client bulunamadı, mock mode'da çalışıyor")
	}

	// Veri toplayıcı başlatma
	collector := collector.NewDataCollector(k8sClient, &config.Metrics)
	go collector.Start(context.Background())

	// AI Scheduler başlatma
	aiScheduler := scheduler.NewAIScheduler(k8sClient, collector, &config.Scheduler)
	go aiScheduler.Start(context.Background())

	// HTTP API başlatma
	router := gin.Default()
	api.SetupRoutes(router, aiScheduler, collector)

	// Server ayarları
	addr := fmt.Sprintf("%s:%d", config.Server.Host, config.Server.Port)
	srv := &http.Server{
		Addr:         addr,
		Handler:      router,
		ReadTimeout:  config.Server.ReadTimeout,
		WriteTimeout: config.Server.WriteTimeout,
	}

	// Graceful shutdown
	go func() {
		logrus.Infof("Server %s portunda başlatılıyor", addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logrus.Fatalf("Server başlatılamadı: %v", err)
		}
	}()

	// Shutdown sinyali bekleme
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	logrus.Info("Server kapatılıyor...")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		logrus.Fatal("Server zorla kapatıldı:", err)
	}

	logrus.Info("Server başarıyla kapatıldı")
}

// setupLogging logging ayarlarını yapılandırır
func setupLogging(logConfig *types.LoggingConfig) {
	// Log level
	switch logConfig.Level {
	case "debug":
		logrus.SetLevel(logrus.DebugLevel)
	case "info":
		logrus.SetLevel(logrus.InfoLevel)
	case "warn":
		logrus.SetLevel(logrus.WarnLevel)
	case "error":
		logrus.SetLevel(logrus.ErrorLevel)
	default:
		logrus.SetLevel(logrus.InfoLevel)
	}

	// Log format
	if logConfig.Format == "json" {
		logrus.SetFormatter(&logrus.JSONFormatter{})
	} else {
		logrus.SetFormatter(&logrus.TextFormatter{})
	}

	// Log dosyası (opsiyonel)
	if logConfig.File != "" {
		file, err := os.OpenFile(logConfig.File, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
		if err == nil {
			logrus.SetOutput(file)
		} else {
			logrus.Warnf("Log dosyası açılamadı: %v", err)
		}
	}
}
