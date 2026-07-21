#!/usr/bin/env python3
"""
Bober-Drive Dashboard — веб-интерфейс для просмотра статистики демона
Минимальный, быстрый, без лишних зависимостей (ponytail дух)

Usage:
    python driver/dashboard.py --project /path/to/docs --port 8000
    
    Откройте http://localhost:8000 в браузере
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import argparse

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

# Relative import for daemon
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from nexus_autonomous_daemon import create_autonomous_daemon, NexusAutonomousDaemon, DaemonState


# ============================================================================
# Configuration
# ============================================================================

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Global daemon instance
_daemon: Optional[NexusAutonomousDaemon] = None
_daemon_lock = asyncio.Lock()


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Bober-Drive Dashboard",
    description="Real-time monitoring and statistics for Bober-Drive v3.0.1",
    version="3.0.1"
)


# ============================================================================
# HTML Dashboard (embedded)
# ============================================================================

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bober-Drive Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 28px;
            font-weight: 600;
            color: #2d3748;
        }
        
        .header .status {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 14px;
            padding: 8px 16px;
            background: #f0f4f8;
            border-radius: 8px;
        }
        
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        .status-dot.ready {
            background: #48bb78;
        }
        
        .status-dot.initializing {
            background: #ed8936;
        }
        
        .status-dot.stopped {
            background: #f56565;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        
        .metric-card.cache {
            border-left-color: #f6ad55;
        }
        
        .metric-card.search {
            border-left-color: #9f7aea;
        }
        
        .metric-label {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            color: #a0aec0;
            margin-bottom: 8px;
        }
        
        .metric-value {
            font-size: 32px;
            font-weight: 700;
            color: #2d3748;
        }
        
        .metric-unit {
            font-size: 14px;
            color: #718096;
            margin-left: 8px;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .chart-container {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        
        .chart-title {
            font-size: 16px;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 20px;
        }
        
        .logs {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        
        .logs-title {
            font-size: 16px;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 15px;
        }
        
        .logs-content {
            background: #1a202c;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: #e2e8f0;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        
        .log-line {
            margin: 4px 0;
            padding: 2px 0;
        }
        
        .log-info { color: #63b3ed; }
        .log-warn { color: #f6ad55; }
        .log-error { color: #fc8181; }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            color: rgba(255,255,255,0.8);
            font-size: 12px;
        }
        
        .connection-status {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #48bb78;
            margin-right: 8px;
        }
        
        .connection-status.disconnected {
            background: #f56565;
        }
        
        @media (max-width: 768px) {
            .header {
                flex-direction: column;
                gap: 20px;
            }
            
            .charts-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div>
                <h1>🔍 Bober-Drive Dashboard</h1>
                <p style="font-size: 12px; color: #718096; margin-top: 5px;">v3.0.1 | Real-time Monitoring</p>
            </div>
            <div class="status">
                <span class="connection-status" id="ws-status"></span>
                <span id="daemon-state">Loading...</span>
                <span style="margin-left: 20px;" id="uptime">Uptime: --</span>
            </div>
        </div>
        
        <!-- Key Metrics -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">📁 Files Scanned</div>
                <div class="metric-value"><span id="files-scanned">0</span><span class="metric-unit">files</span></div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">✅ Files Indexed</div>
                <div class="metric-value"><span id="files-indexed">0</span><span class="metric-unit">files</span></div>
            </div>
            
            <div class="metric-card search">
                <div class="metric-label">🔎 Searches</div>
                <div class="metric-value"><span id="search-queries">0</span><span class="metric-unit">total</span></div>
            </div>
            
            <div class="metric-card cache">
                <div class="metric-label">⚡ Cache Hit Rate</div>
                <div class="metric-value"><span id="cache-hit-rate">0</span><span class="metric-unit">%</span></div>
            </div>
        </div>
        
        <!-- Detailed Metrics -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">💾 Cache Size</div>
                <div class="metric-value"><span id="cache-size">0</span><span class="metric-unit">MB</span></div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">🎯 Avg Search Time</div>
                <div class="metric-value"><span id="avg-search-time">0</span><span class="metric-unit">ms</span></div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">⏱️ Startup Time</div>
                <div class="metric-value"><span id="startup-time">0</span><span class="metric-unit">ms</span></div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">🔄 Reindex Queue</div>
                <div class="metric-value"><span id="reindex-queue">0</span><span class="metric-unit">pending</span></div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="charts-grid">
            <div class="chart-container">
                <div class="chart-title">Indexing Progress</div>
                <canvas id="indexing-chart"></canvas>
            </div>
            
            <div class="chart-container">
                <div class="chart-title">Cache Performance</div>
                <canvas id="cache-chart"></canvas>
            </div>
        </div>
        
        <!-- Logs -->
        <div class="logs">
            <div class="logs-title">📋 Live Status</div>
            <div class="logs-content" id="logs-content">
                <div class="log-line log-info">Waiting for connection...</div>
            </div>
        </div>
        
        <div class="footer">
            <p>🚀 Bober-Drive v3.0.1 | Powered by FastAPI + Chart.js</p>
        </div>
    </div>
    
    <script>
        // Configuration
        const WS_URL = `ws://${window.location.host}/ws/metrics`;
        let ws = null;
        let logLines = [];
        const MAX_LOGS = 50;
        
        // Chart instances
        let indexingChart = null;
        let cacheChart = null;
        
        // Initialize
        function init() {
            initCharts();
            connectWebSocket();
        }
        
        function initCharts() {
            const ctx1 = document.getElementById('indexing-chart').getContext('2d');
            indexingChart = new Chart(ctx1, {
                type: 'doughnut',
                data: {
                    labels: ['Indexed', 'Remaining'],
                    datasets: [{
                        data: [0, 100],
                        backgroundColor: ['#667eea', '#e2e8f0'],
                        borderColor: ['#667eea', '#e2e8f0'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
            
            const ctx2 = document.getElementById('cache-chart').getContext('2d');
            cacheChart = new Chart(ctx2, {
                type: 'bar',
                data: {
                    labels: ['Cache Hits', 'Cache Misses'],
                    datasets: [{
                        label: 'Count',
                        data: [0, 0],
                        backgroundColor: ['#48bb78', '#f56565'],
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
        
        function connectWebSocket() {
            ws = new WebSocket(WS_URL);
            
            ws.onopen = () => {
                console.log('WebSocket connected');
                updateStatus('Connected', true);
                addLog('WebSocket connected', 'info');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                updateStatus('Error', false);
                addLog('WebSocket error', 'error');
            };
            
            ws.onclose = () => {
                console.log('WebSocket closed');
                updateStatus('Disconnected', false);
                addLog('WebSocket disconnected, reconnecting...', 'warn');
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        function updateStatus(state, connected) {
            document.getElementById('ws-status').className = 
                connected ? 'connection-status' : 'connection-status disconnected';
            document.getElementById('daemon-state').textContent = state;
        }
        
        function updateDashboard(data) {
            // Update metrics
            document.getElementById('daemon-state').textContent = data.state || 'Unknown';
            document.getElementById('files-scanned').textContent = data.files_scanned || 0;
            document.getElementById('files-indexed').textContent = data.files_indexed || 0;
            document.getElementById('search-queries').textContent = data.search_queries || 0;
            document.getElementById('cache-hit-rate').textContent = 
                (data.cache_hit_rate || 0).toFixed(1);
            document.getElementById('cache-size').textContent = 
                (data.cache_size_mb || 0).toFixed(1);
            document.getElementById('avg-search-time').textContent = 
                (data.avg_search_time_ms || 0).toFixed(1);
            document.getElementById('startup-time').textContent = 
                (data.startup_time_ms || 0).toFixed(0);
            document.getElementById('reindex-queue').textContent = data.reindex_queue || 0;
            
            // Update uptime
            const uptime = data.uptime || 0;
            const uptimeStr = formatUptime(uptime);
            document.getElementById('uptime').textContent = `Uptime: ${uptimeStr}`;
            
            // Update charts
            if (data.files_scanned > 0) {
                indexingChart.data.datasets[0].data = [
                    data.files_indexed || 0,
                    Math.max(0, (data.files_scanned || 0) - (data.files_indexed || 0))
                ];
                indexingChart.update('none');
            }
            
            const cacheHits = data.cache_hits || 0;
            const totalReads = data.total_reads || 0;
            const cacheMisses = Math.max(0, totalReads - cacheHits);
            cacheChart.data.datasets[0].data = [cacheHits, cacheMisses];
            cacheChart.update('none');
            
            // Log update
            if (data.message) {
                addLog(data.message, 'info');
            }
        }
        
        function addLog(message, level = 'info') {
            const timestamp = new Date().toLocaleTimeString();
            logLines.unshift(`[${timestamp}] ${message}`);
            logLines = logLines.slice(0, MAX_LOGS);
            
            const content = document.getElementById('logs-content');
            content.innerHTML = logLines.map(line => 
                `<div class="log-line log-${level}">${escapeHtml(line)}</div>`
            ).join('');
            content.scrollTop = 0;
        }
        
        function formatUptime(seconds) {
            if (seconds < 60) return `${Math.floor(seconds)}s`;
            if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
            return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
        }
        
        function escapeHtml(text) {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return text.replace(/[&<>"']/g, m => map[m]);
        }
        
        // Start
        window.addEventListener('DOMContentLoaded', init);
    </script>
</body>
</html>
"""


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_class=Response)
async def get_dashboard():
    """Serve dashboard HTML"""
    return Response(
        content=HTML_DASHBOARD,
        media_type="text/html"
    )


@app.get("/api/status")
async def get_status() -> Dict[str, Any]:
    """Get current daemon status"""
    async with _daemon_lock:
        if not _daemon:
            return {"error": "Daemon not initialized"}
        
        status = _daemon.get_status()
        metrics = _daemon.get_metrics()
        cache_stats = _daemon.get_cache_stats()
        
        return {
            **status,
            **metrics,
            **cache_stats,
            "timestamp": datetime.now().isoformat()
        }


@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket endpoint for real-time metrics streaming"""
    await websocket.accept()
    
    try:
        while True:
            async with _daemon_lock:
                if _daemon:
                    status = _daemon.get_status()
                    metrics = _daemon.get_metrics()
                    cache_stats = _daemon.get_cache_stats()
                    
                    data = {
                        "state": status.get("state", "UNKNOWN"),
                        "files_scanned": metrics.get("total_files_scanned", 0),
                        "files_indexed": metrics.get("total_files_indexed", 0),
                        "search_queries": metrics.get("search_queries", 0),
                        "avg_search_time_ms": metrics.get("avg_search_time_ms", 0),
                        "startup_time_ms": metrics.get("startup_time_ms", 0),
                        "reindex_queue": metrics.get("reindex_queue_size", 0),
                        "uptime": status.get("uptime", 0),
                        "cache_hit_rate": cache_stats.get("cache_hit_rate_pct", 0) 
                            if cache_stats.get("cache_enabled") else 0,
                        "cache_size_mb": cache_stats.get("size_mb", 0),
                        "cache_hits": cache_stats.get("hits", 0),
                        "total_reads": cache_stats.get("reader_stats", {}).get("total_reads", 0),
                        "message": f"Monitoring: {metrics.get('total_files_indexed', 0)} files indexed"
                    }
                    
                    await websocket.send_json(data)
            
            await asyncio.sleep(1.0)  # Update every second
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass


# ============================================================================
# Startup/Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize daemon on startup"""
    global _daemon
    
    if not _daemon:
        project_root = Path(app.state.project_root or "./docs")
        vault_path = Path(app.state.vault_path or "./.nexus/vault")
        
        logger.info(f"Initializing daemon for {project_root}")
        
        try:
            _daemon = create_autonomous_daemon(
                project_root=project_root,
                vault_path=vault_path,
                enable_file_watch=True
            )
            
            if _daemon.start():
                logger.info("Daemon started successfully")
            else:
                logger.error("Failed to start daemon")
                
        except Exception as e:
            logger.error(f"Failed to initialize daemon: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shutdown daemon"""
    global _daemon
    
    if _daemon:
        logger.info("Shutting down daemon...")
        _daemon.stop(graceful=True)
        _daemon = None


# ============================================================================
# Main
# ============================================================================

def main():
    """Start dashboard server"""
    parser = argparse.ArgumentParser(
        description="Bober-Drive Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python driver/dashboard.py
  python driver/dashboard.py --project ./docs --port 8000
  python driver/dashboard.py --project /home/user/documentation --vault .nexus/vault
        """
    )
    
    parser.add_argument(
        "--project",
        type=str,
        default="./docs",
        help="Path to project documentation (default: ./docs)"
    )
    
    parser.add_argument(
        "--vault",
        type=str,
        default="./.nexus/vault",
        help="Path to vault storage (default: ./.nexus/vault)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run dashboard on (default: 8000)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    
    args = parser.parse_args()
    
    # Pass config to app
    app.state.project_root = args.project
    app.state.vault_path = args.vault
    
    logger.info(f"Starting Bober-Drive Dashboard on http://{args.host}:{args.port}")
    logger.info(f"Project root: {args.project}")
    logger.info(f"Vault path: {args.vault}")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
