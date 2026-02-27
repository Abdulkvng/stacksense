"""
StackSense Ultimate Testing Hub

One unified dashboard for ALL testing:
- Gateway Performance Tests
- Unit Tests (pytest)
- Benchmark Tests
- Live Monitoring
- Comprehensive Metrics
- Real-time Visualizations

Run with:
    python tests/unified_testing_hub.py

Then open: http://localhost:9000
"""

import asyncio
import subprocess
import json
import time
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

# Import test components
from test_gateway_live import LiveTestRunner

app = FastAPI(title="StackSense Ultimate Testing Hub")

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Test runners
gateway_runner = None
unit_test_results = []
benchmark_results = {}
live_metrics = {
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "running": 0,
    "avg_latency": 0,
    "total_duration": 0
}


@app.get("/", response_class=HTMLResponse)
async def get_hub():
    """Serve the unified testing hub."""
    return UNIFIED_HUB_HTML


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for live updates."""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/api/run/gateway-tests")
async def run_gateway_tests():
    """Run gateway performance tests."""
    global gateway_runner

    gateway_runner = LiveTestRunner()

    # Override broadcast
    async def ws_broadcast(data: dict):
        await manager.broadcast({"type": "gateway", **data})

    gateway_runner.broadcast_update = ws_broadcast

    # Run in background
    asyncio.create_task(run_gateway_tests_async())

    return {"status": "started", "test_type": "gateway"}


async def run_gateway_tests_async():
    """Run gateway tests async."""
    await gateway_runner.run_all_tests()

    # Update metrics
    passed = sum(1 for r in gateway_runner.results if r.status == "passed")
    failed = sum(1 for r in gateway_runner.results if r.status == "failed")

    live_metrics["total_tests"] += len(gateway_runner.results)
    live_metrics["passed"] += passed
    live_metrics["failed"] += failed

    await manager.broadcast({
        "type": "metrics_update",
        "metrics": live_metrics
    })


@app.post("/api/run/unit-tests")
async def run_unit_tests():
    """Run pytest unit tests."""
    asyncio.create_task(run_unit_tests_async())
    return {"status": "started", "test_type": "unit"}


async def run_unit_tests_async():
    """Run unit tests with pytest."""
    await manager.broadcast({
        "type": "unit_test_start",
        "message": "Running pytest unit tests..."
    })

    # Run pytest with JSON output
    result = subprocess.run(
        ["pytest", "tests/", "-v", "--tb=short", "--json-report", "--json-report-file=test_report.json"],
        capture_output=True,
        text=True,
        cwd="/Users/kvng/projects/stacksense"
    )

    # Parse results
    try:
        with open("/Users/kvng/projects/stacksense/test_report.json", "r") as f:
            report = json.load(f)

        await manager.broadcast({
            "type": "unit_test_complete",
            "results": {
                "total": report.get("summary", {}).get("total", 0),
                "passed": report.get("summary", {}).get("passed", 0),
                "failed": report.get("summary", {}).get("failed", 0),
                "skipped": report.get("summary", {}).get("skipped", 0),
                "duration": report.get("duration", 0)
            }
        })

        # Update global metrics
        live_metrics["total_tests"] += report.get("summary", {}).get("total", 0)
        live_metrics["passed"] += report.get("summary", {}).get("passed", 0)
        live_metrics["failed"] += report.get("summary", {}).get("failed", 0)

    except Exception as e:
        await manager.broadcast({
            "type": "unit_test_error",
            "error": str(e),
            "output": result.stdout
        })


@app.post("/api/run/benchmarks")
async def run_benchmarks():
    """Run performance benchmarks."""
    asyncio.create_task(run_benchmarks_async())
    return {"status": "started", "test_type": "benchmark"}


async def run_benchmarks_async():
    """Run benchmark tests."""
    await manager.broadcast({
        "type": "benchmark_start",
        "message": "Running performance benchmarks..."
    })

    # Import and run benchmarks
    from benchmarks.gateway_performance import (
        benchmark_no_gateway,
        benchmark_sync_gateway,
        benchmark_async_gateway,
        benchmark_async_gateway_cached,
        benchmark_concurrent_requests
    )

    messages = [{"role": "user", "content": "Benchmark test"}]
    iterations = 100

    # Run benchmarks
    await manager.broadcast({
        "type": "benchmark_progress",
        "test": "no_gateway",
        "status": "running"
    })

    latencies_baseline = benchmark_no_gateway(messages, "gpt-4", iterations)

    await manager.broadcast({
        "type": "benchmark_progress",
        "test": "sync_gateway",
        "status": "running"
    })

    latencies_sync = benchmark_sync_gateway(messages, "gpt-4", iterations)

    await manager.broadcast({
        "type": "benchmark_progress",
        "test": "async_gateway",
        "status": "running"
    })

    latencies_async = await benchmark_async_gateway(messages, "gpt-4", iterations)

    await manager.broadcast({
        "type": "benchmark_progress",
        "test": "async_cached",
        "status": "running"
    })

    latencies_cached = await benchmark_async_gateway_cached(messages, "gpt-4", iterations)

    await manager.broadcast({
        "type": "benchmark_progress",
        "test": "concurrent",
        "status": "running"
    })

    total_time, throughput = await benchmark_concurrent_requests(messages, "gpt-4", 100)

    # Calculate stats
    import statistics

    results = {
        "baseline": {
            "mean": statistics.mean(latencies_baseline),
            "p50": sorted(latencies_baseline)[int(len(latencies_baseline) * 0.50)],
            "p95": sorted(latencies_baseline)[int(len(latencies_baseline) * 0.95)],
            "p99": sorted(latencies_baseline)[int(len(latencies_baseline) * 0.99)]
        },
        "sync_gateway": {
            "mean": statistics.mean(latencies_sync),
            "p50": sorted(latencies_sync)[int(len(latencies_sync) * 0.50)],
            "p95": sorted(latencies_sync)[int(len(latencies_sync) * 0.95)],
            "p99": sorted(latencies_sync)[int(len(latencies_sync) * 0.99)]
        },
        "async_gateway": {
            "mean": statistics.mean(latencies_async),
            "p50": sorted(latencies_async)[int(len(latencies_async) * 0.50)],
            "p95": sorted(latencies_async)[int(len(latencies_async) * 0.95)],
            "p99": sorted(latencies_async)[int(len(latencies_async) * 0.99)]
        },
        "async_cached": {
            "mean": statistics.mean(latencies_cached),
            "p50": sorted(latencies_cached)[int(len(latencies_cached) * 0.50)],
            "p95": sorted(latencies_cached)[int(len(latencies_cached) * 0.95)],
            "p99": sorted(latencies_cached)[int(len(latencies_cached) * 0.99)]
        },
        "concurrent": {
            "throughput": throughput,
            "total_time": total_time
        }
    }

    await manager.broadcast({
        "type": "benchmark_complete",
        "results": results
    })


@app.post("/api/run/all")
async def run_all_tests():
    """Run ALL tests."""
    await manager.broadcast({
        "type": "all_tests_start",
        "message": "Running comprehensive test suite..."
    })

    # Run all test types
    asyncio.create_task(run_all_tests_async())

    return {"status": "started", "test_type": "all"}


async def run_all_tests_async():
    """Run all tests sequentially."""
    # 1. Gateway tests
    await manager.broadcast({
        "type": "phase",
        "phase": "gateway",
        "message": "Running Gateway Performance Tests..."
    })
    await run_gateway_tests_async()

    # 2. Unit tests
    await manager.broadcast({
        "type": "phase",
        "phase": "unit",
        "message": "Running Unit Tests..."
    })
    await run_unit_tests_async()

    # 3. Benchmarks
    await manager.broadcast({
        "type": "phase",
        "phase": "benchmark",
        "message": "Running Performance Benchmarks..."
    })
    await run_benchmarks_async()

    await manager.broadcast({
        "type": "all_tests_complete",
        "message": "All tests complete!",
        "metrics": live_metrics
    })


@app.get("/api/metrics")
async def get_metrics():
    """Get current metrics."""
    return live_metrics


# Unified Dashboard HTML
UNIFIED_HUB_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StackSense Ultimate Testing Hub</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0118 0%, #1a0b2e 50%, #16213e 100%);
            background-attachment: fixed;
            color: #e2e8f0;
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }

        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background:
                radial-gradient(circle at 20% 50%, rgba(99, 102, 241, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(236, 72, 153, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 40% 20%, rgba(139, 92, 246, 0.1) 0%, transparent 50%);
            pointer-events: none;
            animation: backgroundShift 20s ease infinite;
        }

        @keyframes backgroundShift {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.8; }
        }

        .container {
            max-width: 1920px;
            margin: 0 auto;
            padding: 15px;
            position: relative;
            z-index: 1;
        }

        .header {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px 30px;
            border-radius: 15px;
            margin-bottom: 15px;
            box-shadow:
                0 30px 80px rgba(0, 0, 0, 0.4),
                inset 0 1px 1px rgba(255, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
        }

        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.2) 50%, rgba(236, 72, 153, 0.2) 100%);
            z-index: -1;
        }

        .header h1 {
            font-size: 28px;
            font-weight: 900;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #fff 0%, #a78bfa 50%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1px;
            text-shadow: 0 0 60px rgba(167, 139, 250, 0.5);
        }

        .header p {
            font-size: 13px;
            opacity: 0.95;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .connection-status {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #10b981;
            margin-right: 6px;
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.8);
        }

        @keyframes pulse {
            0%, 100% {
                opacity: 1;
                box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7), 0 0 20px rgba(16, 185, 129, 0.8);
            }
            50% {
                opacity: 0.6;
                box-shadow: 0 0 0 15px rgba(16, 185, 129, 0), 0 0 30px rgba(16, 185, 129, 0.4);
            }
        }

        .control-panel {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 10px;
            margin-bottom: 15px;
        }

        .control-btn {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
            padding: 12px 18px;
            font-size: 13px;
            font-weight: 700;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
        }

        .control-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s;
        }

        .control-btn:hover::before {
            left: 100%;
        }

        .control-btn:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow:
                0 15px 45px rgba(99, 102, 241, 0.4),
                0 0 50px rgba(99, 102, 241, 0.2);
            border-color: rgba(99, 102, 241, 0.5);
            background: rgba(99, 102, 241, 0.2);
        }

        .control-btn:active {
            transform: translateY(-2px) scale(0.98);
        }

        .control-btn.run-all {
            grid-column: 1 / -1;
            background: linear-gradient(135deg, rgba(236, 72, 153, 0.3), rgba(244, 63, 94, 0.3));
            border: 2px solid rgba(236, 72, 153, 0.5);
            font-size: 15px;
            padding: 15px 20px;
            box-shadow:
                0 10px 40px rgba(236, 72, 153, 0.4),
                0 0 60px rgba(236, 72, 153, 0.2);
        }

        .control-btn.run-all:hover {
            box-shadow:
                0 20px 60px rgba(236, 72, 153, 0.6),
                0 0 80px rgba(236, 72, 153, 0.4);
            border-color: rgba(236, 72, 153, 0.8);
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-bottom: 15px;
        }

        .metric-card {
            background: rgba(255, 255, 255, 0.04);
            backdrop-filter: blur(10px);
            padding: 18px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative;
            overflow: hidden;
        }

        .metric-card::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.1) 0%, transparent 70%);
            opacity: 0;
            transition: opacity 0.5s;
        }

        .metric-card:hover::before {
            opacity: 1;
        }

        .metric-card:hover {
            border-color: rgba(99, 102, 241, 0.5);
            transform: translateY(-8px) scale(1.02);
            box-shadow:
                0 20px 60px rgba(99, 102, 241, 0.3),
                0 0 40px rgba(99, 102, 241, 0.1);
        }

        .metric-label {
            font-size: 10px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 10px;
            font-weight: 700;
        }

        .metric-value {
            font-size: 32px;
            font-weight: 900;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1px;
            filter: drop-shadow(0 0 30px rgba(99, 102, 241, 0.5));
        }

        .metric-value.success {
            background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            filter: drop-shadow(0 0 30px rgba(16, 185, 129, 0.5));
        }

        .metric-value.error {
            background: linear-gradient(135deg, #ef4444 0%, #f87171 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            filter: drop-shadow(0 0 30px rgba(239, 68, 68, 0.5));
        }

        .tabs {
            display: flex;
            gap: 6px;
            margin-bottom: 12px;
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            padding: 5px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .tab {
            padding: 10px 20px;
            background: transparent;
            border: none;
            color: #94a3b8;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            border-radius: 10px;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative;
        }

        .tab:hover {
            color: #e2e8f0;
            background: rgba(255, 255, 255, 0.05);
        }

        .tab.active {
            color: #fff;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.4), rgba(139, 92, 246, 0.4));
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }

        .tab-content {
            display: none;
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            min-height: 400px;
            animation: fadeIn 0.5s ease;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .tab-content.active {
            display: block;
        }

        .test-item {
            background: rgba(255, 255, 255, 0.04);
            backdrop-filter: blur(10px);
            padding: 12px 16px;
            margin-bottom: 10px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 4px solid #334155;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative;
            overflow: hidden;
        }

        .test-item::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 5px;
            height: 100%;
            background: linear-gradient(180deg, transparent, currentColor, transparent);
            opacity: 0;
            transition: opacity 0.3s;
        }

        .test-item:hover {
            transform: translateX(8px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
        }

        .test-item.running {
            border-left-color: #f59e0b;
            animation: glow 2s ease-in-out infinite;
            background: rgba(245, 158, 11, 0.05);
        }

        .test-item.passed {
            border-left-color: #10b981;
        }

        .test-item.passed:hover {
            background: rgba(16, 185, 129, 0.05);
        }

        .test-item.failed {
            border-left-color: #ef4444;
        }

        .test-item.failed:hover {
            background: rgba(239, 68, 68, 0.05);
        }

        @keyframes glow {
            0%, 100% {
                box-shadow: 0 0 20px rgba(245, 158, 11, 0.4);
                border-left-color: #f59e0b;
            }
            50% {
                box-shadow: 0 0 40px rgba(245, 158, 11, 0.7), 0 0 60px rgba(245, 158, 11, 0.3);
                border-left-color: #fbbf24;
            }
        }

        .test-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .test-name {
            font-size: 14px;
            font-weight: 700;
            letter-spacing: -0.3px;
        }

        .test-status {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border: 1px solid;
        }

        .test-status.running {
            background: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            border-color: rgba(245, 158, 11, 0.4);
            animation: statusPulse 2s ease infinite;
        }

        @keyframes statusPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        .test-status.passed {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border-color: rgba(16, 185, 129, 0.4);
        }

        .test-status.failed {
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border-color: rgba(239, 68, 68, 0.4);
        }

        .test-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 8px;
            margin-top: 10px;
        }

        .test-metric {
            background: rgba(255, 255, 255, 0.04);
            padding: 8px 10px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            transition: all 0.3s;
        }

        .test-metric:hover {
            background: rgba(255, 255, 255, 0.06);
            border-color: rgba(99, 102, 241, 0.3);
            transform: translateY(-2px);
        }

        .test-metric-label {
            font-size: 9px;
            color: #94a3b8;
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }

        .test-metric-value {
            font-size: 16px;
            font-weight: 800;
            color: #e2e8f0;
            letter-spacing: -0.3px;
        }

        .chart-container {
            background: rgba(255, 255, 255, 0.03);
            padding: 25px;
            border-radius: 20px;
            margin-top: 25px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.3);
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
            width: 0%;
            transition: width 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 0 20px rgba(99, 102, 241, 0.6);
            position: relative;
            overflow: hidden;
        }

        .progress-fill::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            bottom: 0;
            right: 0;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            animation: shimmer 2s infinite;
        }

        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        .log {
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(10px);
            color: #10b981;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid rgba(16, 185, 129, 0.2);
            font-family: 'Courier New', 'Monaco', monospace;
            font-size: 11px;
            max-height: 300px;
            overflow-y: auto;
            line-height: 1.5;
            box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.5);
        }

        .log::-webkit-scrollbar {
            width: 8px;
        }

        .log::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        }

        .log::-webkit-scrollbar-thumb {
            background: rgba(99, 102, 241, 0.5);
            border-radius: 10px;
        }

        .log::-webkit-scrollbar-thumb:hover {
            background: rgba(99, 102, 241, 0.7);
        }

        .log-entry {
            margin-bottom: 4px;
            padding: 2px 0;
            border-left: 2px solid transparent;
            padding-left: 8px;
        }

        .log-entry.error {
            color: #f87171;
            border-left-color: #ef4444;
            background: rgba(239, 68, 68, 0.05);
        }

        .log-entry.success {
            color: #34d399;
            border-left-color: #10b981;
            background: rgba(16, 185, 129, 0.05);
        }

        .log-entry.info {
            color: #60a5fa;
            border-left-color: #3b82f6;
            background: rgba(59, 130, 246, 0.05);
        }

        h2 {
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 StackSense Ultimate Testing Hub</h1>
            <p>
                <span class="connection-status" id="status"></span>
                <span id="connection-text">Connecting...</span>
            </p>
        </div>

        <div class="control-panel">
            <button class="control-btn" onclick="runGatewayTests()">
                🚀 Gateway Tests
            </button>
            <button class="control-btn" onclick="runUnitTests()">
                📋 Unit Tests
            </button>
            <button class="control-btn" onclick="runBenchmarks()">
                ⚡ Benchmarks
            </button>
            <button class="control-btn run-all" onclick="runAllTests()">
                🔥 RUN ALL TESTS
            </button>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Total Tests</div>
                <div class="metric-value" id="total-tests">0</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Passed</div>
                <div class="metric-value success" id="passed-tests">0</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Failed</div>
                <div class="metric-value error" id="failed-tests">0</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Latency</div>
                <div class="metric-value" id="avg-latency">0ms</div>
            </div>
        </div>

        <div class="progress-bar">
            <div class="progress-fill" id="progress"></div>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="switchTab('gateway')">Gateway Tests</button>
            <button class="tab" onclick="switchTab('unit')">Unit Tests</button>
            <button class="tab" onclick="switchTab('benchmarks')">Benchmarks</button>
            <button class="tab" onclick="switchTab('logs')">Live Logs</button>
        </div>

        <div id="gateway-tab" class="tab-content active">
            <h2 style="margin-bottom: 20px;">Gateway Performance Tests</h2>
            <div id="gateway-tests"></div>
        </div>

        <div id="unit-tab" class="tab-content">
            <h2 style="margin-bottom: 20px;">Unit Test Results</h2>
            <div id="unit-tests"></div>
        </div>

        <div id="benchmarks-tab" class="tab-content">
            <h2 style="margin-bottom: 20px;">Performance Benchmarks</h2>
            <div id="benchmark-results"></div>
        </div>

        <div id="logs-tab" class="tab-content">
            <h2 style="margin-bottom: 20px;">Live Execution Logs</h2>
            <div class="log" id="logs"></div>
        </div>
    </div>

    <script>
        let ws;
        let gatewayTests = {};
        let totalTests = 0;
        let passedTests = 0;
        let failedTests = 0;
        let logs = [];

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(protocol + '//' + window.location.host + '/ws');

            ws.onopen = () => {
                document.getElementById('status').style.background = '#10b981';
                document.getElementById('connection-text').textContent = 'Connected';
                addLog('WebSocket connected', 'success');
            };

            ws.onclose = () => {
                document.getElementById('status').style.background = '#ef4444';
                document.getElementById('connection-text').textContent = 'Reconnecting...';
                addLog('WebSocket disconnected, reconnecting...', 'error');
                setTimeout(connectWebSocket, 3000);
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleUpdate(data);
            };
        }

        function handleUpdate(data) {
            console.log('Update:', data);

            if (data.type === 'gateway' && data.test_name) {
                updateGatewayTest(data);
            } else if (data.type === 'test_start') {
                addLog(`Starting: ${data.test_name}`, 'info');
            } else if (data.type === 'test_complete') {
                const result = data.result;
                addLog(`${result.status === 'passed' ? '✅' : '❌'} ${result.test_name} (${result.duration_ms.toFixed(1)}ms)`, result.status === 'passed' ? 'success' : 'error');
                updateMetrics();
            } else if (data.type === 'metrics_update') {
                updateGlobalMetrics(data.metrics);
            } else if (data.type === 'unit_test_complete') {
                displayUnitTestResults(data.results);
            } else if (data.type === 'benchmark_complete') {
                displayBenchmarkResults(data.results);
            } else if (data.type === 'phase') {
                addLog(`📍 ${data.message}`, 'info');
            } else if (data.type === 'all_tests_complete') {
                addLog('🎉 All tests complete!', 'success');
                document.getElementById('progress').style.width = '100%';
            }
        }

        function updateGatewayTest(data) {
            if (data.test_name) {
                gatewayTests[data.test_name] = data;
                renderGatewayTests();
            }
        }

        function renderGatewayTests() {
            const container = document.getElementById('gateway-tests');
            container.innerHTML = '';

            for (const [name, data] of Object.entries(gatewayTests)) {
                const item = document.createElement('div');
                item.className = `test-item ${data.result?.status || 'running'}`;

                let metricsHTML = '';
                if (data.result?.metrics) {
                    metricsHTML = '<div class="test-metrics">';
                    for (const [key, value] of Object.entries(data.result.metrics)) {
                        metricsHTML += `
                            <div class="test-metric">
                                <div class="test-metric-label">${formatKey(key)}</div>
                                <div class="test-metric-value">${formatValue(value)}</div>
                            </div>
                        `;
                    }
                    metricsHTML += '</div>';
                }

                item.innerHTML = `
                    <div class="test-header">
                        <div class="test-name">${name}</div>
                        <div class="test-status ${data.result?.status || 'running'}">
                            ${data.result?.status || 'running'}
                        </div>
                    </div>
                    ${metricsHTML}
                `;

                container.appendChild(item);
            }
        }

        function displayUnitTestResults(results) {
            const container = document.getElementById('unit-tests');
            container.innerHTML = `
                <div class="test-item passed">
                    <div class="test-header">
                        <div class="test-name">Unit Test Suite</div>
                        <div class="test-status passed">Complete</div>
                    </div>
                    <div class="test-metrics">
                        <div class="test-metric">
                            <div class="test-metric-label">Total</div>
                            <div class="test-metric-value">${results.total}</div>
                        </div>
                        <div class="test-metric">
                            <div class="test-metric-label">Passed</div>
                            <div class="test-metric-value">${results.passed}</div>
                        </div>
                        <div class="test-metric">
                            <div class="test-metric-label">Failed</div>
                            <div class="test-metric-value">${results.failed}</div>
                        </div>
                        <div class="test-metric">
                            <div class="test-metric-label">Duration</div>
                            <div class="test-metric-value">${results.duration.toFixed(2)}s</div>
                        </div>
                    </div>
                </div>
            `;

            addLog(`Unit tests: ${results.passed}/${results.total} passed`, 'success');
        }

        function displayBenchmarkResults(results) {
            const container = document.getElementById('benchmark-results');
            let html = '';

            for (const [name, data] of Object.entries(results)) {
                html += `
                    <div class="test-item passed">
                        <div class="test-header">
                            <div class="test-name">${formatKey(name)}</div>
                            <div class="test-status passed">Complete</div>
                        </div>
                        <div class="test-metrics">
                `;

                for (const [metric, value] of Object.entries(data)) {
                    html += `
                        <div class="test-metric">
                            <div class="test-metric-label">${formatKey(metric)}</div>
                            <div class="test-metric-value">${formatValue(value)}</div>
                        </div>
                    `;
                }

                html += `
                        </div>
                    </div>
                `;
            }

            container.innerHTML = html;
            addLog('Benchmarks complete', 'success');
        }

        function updateGlobalMetrics(metrics) {
            document.getElementById('total-tests').textContent = metrics.total_tests;
            document.getElementById('passed-tests').textContent = metrics.passed;
            document.getElementById('failed-tests').textContent = metrics.failed;
            document.getElementById('avg-latency').textContent = metrics.avg_latency.toFixed(1) + 'ms';
        }

        function updateMetrics() {
            // Update from gateway tests
            const results = Object.values(gatewayTests).map(t => t.result).filter(Boolean);
            passedTests = results.filter(r => r.status === 'passed').length;
            failedTests = results.filter(r => r.status === 'failed').length;
            totalTests = results.length;

            document.getElementById('total-tests').textContent = totalTests;
            document.getElementById('passed-tests').textContent = passedTests;
            document.getElementById('failed-tests').textContent = failedTests;

            const progress = totalTests > 0 ? (passedTests + failedTests) / totalTests * 100 : 0;
            document.getElementById('progress').style.width = progress + '%';
        }

        function addLog(message, type = 'info') {
            const timestamp = new Date().toLocaleTimeString();
            logs.push({ timestamp, message, type });

            const logContainer = document.getElementById('logs');
            const entry = document.createElement('div');
            entry.className = `log-entry ${type}`;
            entry.textContent = `[${timestamp}] ${message}`;
            logContainer.appendChild(entry);
            logContainer.scrollTop = logContainer.scrollHeight;
        }

        async function runGatewayTests() {
            addLog('Starting Gateway Performance Tests...', 'info');
            await fetch('/api/run/gateway-tests', { method: 'POST' });
        }

        async function runUnitTests() {
            addLog('Starting Unit Tests...', 'info');
            await fetch('/api/run/unit-tests', { method: 'POST' });
        }

        async function runBenchmarks() {
            addLog('Starting Benchmarks...', 'info');
            await fetch('/api/run/benchmarks', { method: 'POST' });
        }

        async function runAllTests() {
            addLog('🔥 Starting comprehensive test suite...', 'info');
            gatewayTests = {};
            totalTests = 0;
            passedTests = 0;
            failedTests = 0;
            document.getElementById('progress').style.width = '0%';

            await fetch('/api/run/all', { method: 'POST' });
        }

        function switchTab(tab) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');

            // Update tab content
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById(tab + '-tab').classList.add('active');
        }

        function formatKey(key) {
            return key.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
        }

        function formatValue(value) {
            if (typeof value === 'number') {
                return value.toFixed(2);
            }
            return value;
        }

        // Connect on load
        connectWebSocket();
        addLog('Testing Hub initialized', 'success');
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    print("=" * 80)
    print("🧪 StackSense Ultimate Testing Hub")
    print("=" * 80)
    print("\n✨ One dashboard for ALL testing:")
    print("   • Gateway Performance Tests")
    print("   • Unit Tests (pytest)")
    print("   • Performance Benchmarks")
    print("   • Live Monitoring")
    print("   • Comprehensive Metrics")
    print("\nStarting server...")
    print("🌐 Dashboard: http://localhost:9000")
    print("\n⚠️  Press Ctrl+C to stop")
    print("=" * 80)

    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")
