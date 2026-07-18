#!/usr/bin/env python3
"""
Observability Layer - Metrics, logging, and tracing
Provides visibility into system behavior and performance.
"""

import logging
import time
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics"""
    COUNTER = "counter"  # Monotonically increasing
    GAUGE = "gauge"      # Current value
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"      # Duration measurements


@dataclass
class Metric:
    """Represents a metric"""
    name: str
    metric_type: MetricType
    value: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'type': self.metric_type.value,
            'value': self.value,
            'timestamp': self.timestamp,
            'tags': self.tags
        }


@dataclass
class HistogramStats:
    """Statistics for histogram metric"""
    min: float = float('inf')
    max: float = float('-inf')
    sum: float = 0.0
    count: int = 0
    avg: float = 0.0
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    
    def add_value(self, value: float) -> None:
        """Add value to histogram"""
        self.min = min(self.min, value)
        self.max = max(self.max, value)
        self.sum += value
        self.count += 1
        self.avg = self.sum / self.count
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            'min': self.min if self.count > 0 else 0.0,
            'max': self.max if self.count > 0 else 0.0,
            'sum': self.sum,
            'count': self.count,
            'avg': self.avg
        }


class MetricsCollector:
    """Central metrics collection system"""
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        
        # Metric storage
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        
        # Computed stats
        self._histogram_stats: Dict[str, HistogramStats] = {}
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        logger.info("MetricsCollector initialized")
    
    def increment_counter(self, name: str, value: float = 1.0, 
                         tags: Optional[Dict[str, str]] = None) -> None:
        """Increment counter metric"""
        with self._lock:
            key = self._make_key(name, tags)
            self._counters[key] = self._counters.get(key, 0.0) + value
    
    def set_gauge(self, name: str, value: float,
                 tags: Optional[Dict[str, str]] = None) -> None:
        """Set gauge metric"""
        with self._lock:
            key = self._make_key(name, tags)
            self._gauges[key] = value
    
    def record_histogram(self, name: str, value: float,
                        tags: Optional[Dict[str, str]] = None) -> None:
        """Record histogram value"""
        with self._lock:
            key = self._make_key(name, tags)
            
            if key not in self._histograms:
                self._histograms[key] = []
                self._histogram_stats[key] = HistogramStats()
            
            self._histograms[key].append(value)
            self._histogram_stats[key].add_value(value)
            
            # Keep only recent values
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]
    
    def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """Get counter value"""
        with self._lock:
            key = self._make_key(name, tags)
            return self._counters.get(key, 0.0)
    
    def get_gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value"""
        with self._lock:
            key = self._make_key(name, tags)
            return self._gauges.get(key, 0.0)
    
    def get_histogram_stats(self, name: str, 
                           tags: Optional[Dict[str, str]] = None) -> Optional[Dict[str, float]]:
        """Get histogram statistics"""
        with self._lock:
            key = self._make_key(name, tags)
            if key in self._histogram_stats:
                return self._histogram_stats[key].to_dict()
            return None
    
    def _make_key(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Make metric key with tags"""
        if not tags:
            return name
        tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics"""
        with self._lock:
            return {
                'counters': self._counters.copy(),
                'gauges': self._gauges.copy(),
                'histogram_stats': {k: v.to_dict() for k, v in self._histogram_stats.items()}
            }
    
    def reset(self) -> None:
        """Reset all metrics"""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._histogram_stats.clear()
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        with self._lock:
            # Counters
            for key, value in self._counters.items():
                lines.append(f"{key}_total {value}")
            
            # Gauges
            for key, value in self._gauges.items():
                lines.append(f"{key} {value}")
            
            # Histogram stats
            for key, stats in self._histogram_stats.items():
                lines.append(f"{key}_min {stats.min}")
                lines.append(f"{key}_max {stats.max}")
                lines.append(f"{key}_avg {stats.avg}")
                lines.append(f"{key}_count {stats.count}")
        
        return '\n'.join(lines)


class StructuredLogger:
    """Structured logging with metadata"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info with structured data"""
        self._log_structured(logging.INFO, message, kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error with structured data"""
        self._log_structured(logging.ERROR, message, kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning with structured data"""
        self._log_structured(logging.WARNING, message, kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug with structured data"""
        self._log_structured(logging.DEBUG, message, kwargs)
    
    def _log_structured(self, level: int, message: str, data: Dict[str, Any]) -> None:
        """Log with structured metadata"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': logging.getLevelName(level),
            'message': message,
            **data
        }
        self.logger.log(level, json.dumps(log_entry))


@dataclass
class TraceSpan:
    """Represents a trace span"""
    span_id: str
    trace_id: str
    operation: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "running"
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    def finish(self, status: str = "completed") -> None:
        """Finish the span"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
    
    def add_tag(self, key: str, value: str) -> None:
        """Add tag to span"""
        self.tags[key] = value
    
    def add_log(self, message: str, **kwargs) -> None:
        """Add log to span"""
        self.logs.append({
            'timestamp': datetime.utcnow().isoformat(),
            'message': message,
            **kwargs
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'span_id': self.span_id,
            'trace_id': self.trace_id,
            'operation': self.operation,
            'duration_ms': self.duration_ms,
            'status': self.status,
            'tags': self.tags,
            'logs': self.logs
        }


class DistributedTracer:
    """Distributed tracing system"""
    
    def __init__(self):
        self._spans: Dict[str, List[TraceSpan]] = {}
        self._lock = threading.Lock()
        logger.info("DistributedTracer initialized")
    
    def start_span(self, trace_id: str, operation: str) -> TraceSpan:
        """Start a new span"""
        import uuid
        span_id = str(uuid.uuid4())
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            operation=operation
        )
        
        with self._lock:
            if trace_id not in self._spans:
                self._spans[trace_id] = []
            self._spans[trace_id].append(span)
        
        logger.debug(f"Started span: {operation} ({span_id})")
        return span
    
    def get_trace(self, trace_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get complete trace"""
        with self._lock:
            spans = self._spans.get(trace_id)
            if spans:
                return [span.to_dict() for span in spans]
            return None
    
    def get_all_traces(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all traces"""
        with self._lock:
            return {
                trace_id: [span.to_dict() for span in spans]
                for trace_id, spans in self._spans.items()
            }
    
    def cleanup_old_traces(self, older_than_hours: int = 24) -> int:
        """Clean up old traces"""
        cutoff_time = time.time() - (older_than_hours * 3600)
        removed_count = 0
        
        with self._lock:
            trace_ids_to_remove = []
            for trace_id, spans in self._spans.items():
                if spans and spans[0].start_time < cutoff_time:
                    trace_ids_to_remove.append(trace_id)
            
            for trace_id in trace_ids_to_remove:
                del self._spans[trace_id]
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old traces")
        return removed_count
