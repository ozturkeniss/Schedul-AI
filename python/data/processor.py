#!/usr/bin/env python3
"""
Data Processing Module
Go backend'den gelen verileri işler ve AI için hazırlar
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()

class DataProcessor:
    """Veri işleme sınıfı"""
    
    def __init__(self):
        self.node_history = {}  # Node geçmiş verileri
        self.pod_history = {}   # Pod geçmiş verileri
        self.feature_cache = {} # Feature cache
        
    def process_cluster_state(self, cluster_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cluster state verilerini işler"""
        try:
            nodes = cluster_data.get('nodes', [])
            processed_nodes = []
            
            for node in nodes:
                processed_node = self._process_node_data(node)
                processed_nodes.append(processed_node)
                
                # Node geçmişini güncelle
                self._update_node_history(processed_node)
            
            # Cluster seviyesi özellikler
            cluster_features = self._extract_cluster_features(processed_nodes)
            
            return {
                'nodes': processed_nodes,
                'cluster_features': cluster_features,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Cluster state processing failed", error=str(e))
            return {}
    
    def _process_node_data(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Node verilerini işler"""
        try:
            # Temel özellikler
            node_name = node.get('name', 'unknown')
            cpu_usage = float(node.get('cpu_usage', 0))
            memory_usage = float(node.get('memory_usage', 0))
            is_ready = bool(node.get('ready', False))
            taints = node.get('taints', [])
            
            # Hesaplanmış özellikler
            resource_score = self._calculate_resource_score(cpu_usage, memory_usage)
            taint_penalty = self._calculate_taint_penalty(taints)
            readiness_score = 1.0 if is_ready else 0.0
            
            # Geçmiş verilerden özellikler
            historical_features = self._extract_historical_features(node_name)
            
            return {
                'name': node_name,
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'ready': is_ready,
                'taints': taints,
                'resource_score': resource_score,
                'taint_penalty': taint_penalty,
                'readiness_score': readiness_score,
                'historical_features': historical_features,
                'total_score': resource_score + readiness_score + taint_penalty + historical_features.get('stability_score', 0)
            }
            
        except Exception as e:
            logger.error("Node data processing failed", node=node.get('name'), error=str(e))
            return node
    
    def _calculate_resource_score(self, cpu_usage: float, memory_usage: float) -> float:
        """Resource kullanımına göre skor hesaplar"""
        # CPU ve memory kullanımı düşükse yüksek skor
        cpu_score = max(0, 100 - cpu_usage) / 100
        memory_score = max(0, 100 - memory_usage) / 100
        
        # Ağırlıklı ortalama
        return (cpu_score * 0.6) + (memory_score * 0.4)
    
    def _calculate_taint_penalty(self, taints: List[str]) -> float:
        """Taint'lere göre penalty hesaplar"""
        if not taints:
            return 0.0
        
        # Her taint için -10 puan
        return -len(taints) * 10.0
    
    def _extract_historical_features(self, node_name: str) -> Dict[str, float]:
        """Node geçmiş verilerinden özellik çıkarır"""
        if node_name not in self.node_history:
            return {
                'stability_score': 0.0,
                'avg_cpu_usage': 0.0,
                'avg_memory_usage': 0.0,
                'failure_rate': 0.0
            }
        
        history = self.node_history[node_name]
        
        if not history:
            return {
                'stability_score': 0.0,
                'avg_cpu_usage': 0.0,
                'avg_memory_usage': 0.0,
                'failure_rate': 0.0
            }
        
        # Son 10 kayıt
        recent_data = history[-10:]
        
        avg_cpu = np.mean([d.get('cpu_usage', 0) for d in recent_data])
        avg_memory = np.mean([d.get('memory_usage', 0) for d in recent_data])
        
        # Kararlılık skoru (düşük varyans = yüksek kararlılık)
        cpu_variance = np.var([d.get('cpu_usage', 0) for d in recent_data])
        memory_variance = np.var([d.get('memory_usage', 0) for d in recent_data])
        
        stability_score = max(0, 100 - (cpu_variance + memory_variance)) / 100
        
        return {
            'stability_score': stability_score,
            'avg_cpu_usage': avg_cpu,
            'avg_memory_usage': avg_memory,
            'failure_rate': 0.0  # TODO: Pod failure rate hesapla
        }
    
    def _update_node_history(self, node_data: Dict[str, Any]):
        """Node geçmiş verilerini günceller"""
        node_name = node_data.get('name')
        if not node_name:
            return
        
        if node_name not in self.node_history:
            self.node_history[node_name] = []
        
        # Timestamp ekle
        node_data['timestamp'] = datetime.utcnow()
        
        # Son 100 kayıt tut
        self.node_history[node_name].append(node_data)
        if len(self.node_history[node_name]) > 100:
            self.node_history[node_name] = self.node_history[node_name][-100:]
    
    def _extract_cluster_features(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cluster seviyesi özellikler çıkarır"""
        if not nodes:
            return {}
        
        # Cluster seviyesi istatistikler
        total_nodes = len(nodes)
        ready_nodes = len([n for n in nodes if n.get('ready', False)])
        avg_cpu = np.mean([n.get('cpu_usage', 0) for n in nodes])
        avg_memory = np.mean([n.get('memory_usage', 0) for n in nodes])
        
        # Cluster sağlık skoru
        health_score = (ready_nodes / total_nodes) * 100 if total_nodes > 0 else 0
        
        return {
            'total_nodes': total_nodes,
            'ready_nodes': ready_nodes,
            'avg_cpu_usage': avg_cpu,
            'avg_memory_usage': avg_memory,
            'health_score': health_score,
            'resource_pressure': (avg_cpu + avg_memory) / 2
        }
    
    def extract_ai_features(self, cluster_data: Dict[str, Any], pod_spec: Dict[str, Any]) -> Dict[str, Any]:
        """AI modeli için özellik çıkarır"""
        try:
            nodes = cluster_data.get('nodes', [])
            cluster_features = cluster_data.get('cluster_features', {})
            
            # Pod resource requirements
            pod_cpu = self._extract_pod_cpu_request(pod_spec)
            pod_memory = self._extract_pod_memory_request(pod_spec)
            
            # Node özellikleri
            node_features = []
            for node in nodes:
                node_feature = {
                    'node_name': node.get('name'),
                    'cpu_usage': node.get('cpu_usage', 0),
                    'memory_usage': node.get('memory_usage', 0),
                    'resource_score': node.get('resource_score', 0),
                    'readiness_score': node.get('readiness_score', 0),
                    'taint_penalty': node.get('taint_penalty', 0),
                    'stability_score': node.get('historical_features', {}).get('stability_score', 0),
                    'total_score': node.get('total_score', 0)
                }
                node_features.append(node_feature)
            
            # AI için feature vector
            ai_features = {
                'pod_requirements': {
                    'cpu_request': pod_cpu,
                    'memory_request': pod_memory
                },
                'cluster_state': {
                    'total_nodes': cluster_features.get('total_nodes', 0),
                    'ready_nodes': cluster_features.get('ready_nodes', 0),
                    'avg_cpu_usage': cluster_features.get('avg_cpu_usage', 0),
                    'avg_memory_usage': cluster_features.get('avg_memory_usage', 0),
                    'health_score': cluster_features.get('health_score', 0),
                    'resource_pressure': cluster_features.get('resource_pressure', 0)
                },
                'node_features': node_features,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info("AI features extracted", 
                       node_count=len(node_features),
                       pod_cpu=pod_cpu,
                       pod_memory=pod_memory)
            
            return ai_features
            
        except Exception as e:
            logger.error("AI feature extraction failed", error=str(e))
            return {}
    
    def _extract_pod_cpu_request(self, pod_spec: Dict[str, Any]) -> float:
        """Pod CPU request'ini çıkarır"""
        try:
            containers = pod_spec.get('containers', [])
            total_cpu = 0.0
            
            for container in containers:
                resources = container.get('resources', {})
                requests = resources.get('requests', {})
                cpu_str = requests.get('cpu', '0')
                
                # CPU string'ini float'a çevir (100m -> 0.1)
                if cpu_str.endswith('m'):
                    cpu_value = float(cpu_str[:-1]) / 1000
                else:
                    cpu_value = float(cpu_str)
                
                total_cpu += cpu_value
            
            return total_cpu
            
        except Exception as e:
            logger.error("Pod CPU extraction failed", error=str(e))
            return 0.0
    
    def _extract_pod_memory_request(self, pod_spec: Dict[str, Any]) -> float:
        """Pod memory request'ini çıkarır"""
        try:
            containers = pod_spec.get('containers', [])
            total_memory = 0.0
            
            for container in containers:
                resources = container.get('resources', {})
                requests = resources.get('requests', {})
                memory_str = requests.get('memory', '0')
                
                # Memory string'ini Mi'ye çevir
                if memory_str.endswith('Mi'):
                    memory_value = float(memory_str[:-2])
                elif memory_str.endswith('Gi'):
                    memory_value = float(memory_str[:-2]) * 1024
                else:
                    memory_value = float(memory_str) / (1024 * 1024)  # bytes to Mi
                
                total_memory += memory_value
            
            return total_memory
            
        except Exception as e:
            logger.error("Pod memory extraction failed", error=str(e))
            return 0.0
    
    def get_processed_data_summary(self) -> Dict[str, Any]:
        """İşlenmiş veri özeti döndürür"""
        return {
            'node_history_count': len(self.node_history),
            'nodes_tracked': list(self.node_history.keys()),
            'feature_cache_size': len(self.feature_cache),
            'last_update': datetime.utcnow().isoformat()
        } 