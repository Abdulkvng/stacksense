"""
StackSense Live Testing Dashboard

Real-time web dashboard for monitoring test execution, metrics, and performance.

Run with:
    python tests/dashboard_server.py

Then open: http://localhost:8080
"""

import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List
import json
from datetime import datetime

# Import test runner
from test_gateway_live import LiveTestRunner

app = FastAPI(title="StackSense Testing Dashboard")

# WebSocket connections
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
test_runner = None


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the live dashboard HTML."""
    return HTML_DASHBOARD


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/api/run-tests")
async def run_tests():
    """Start test suite execution."""
    global test_runner

    # Create new test runner
    test_runner = LiveTestRunner()

    # Override broadcast to send to WebSocket
    original_broadcast = test_runner.broadcast_update

    async def ws_broadcast(data: dict):
        await manager.broadcast(data)
        await original_broadcast(data)

    test_runner.broadcast_update = ws_broadcast

    # Run tests in background
    asyncio.create_task(test_runner.run_all_tests())

    return {"status": "started"}


@app.get("/api/results")
async def get_results():
    """Get current test results."""
    if test_runner is None:
        return {"results": []}

    return {
        "results": [
            {
                "test_name": r.test_name,
                "status": r.status,
                "duration_ms": r.duration_ms,
                "metrics": r.metrics,
                "timestamp": r.timestamp,
                "error": r.error
            }
            for r in test_runner.results
        ]
    }


# HTML Dashboard (embedded)
HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StackSense Live Testing Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }

        .header h1 {
            font-size: 32px;
            color: #667eea;
            margin-bottom: 10px;
        }

        .header p {
            color: #666;
            font-size: 16px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }

        .stat-card:hover {
            transform: translateY(-5px);
        }

        .stat-label {
            font-size: 14px;
            color: #999;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }

        .stat-value {
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
        }

        .stat-value.success {
            color: #10b981;
        }

        .stat-value.error {
            color: #ef4444;
        }

        .stat-value.warning {
            color: #f59e0b;
        }

        .tests-container {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }

        .test-item {
            padding: 20px;
            border-left: 4px solid #e5e7eb;
            margin-bottom: 15px;
            border-radius: 8px;
            background: #f9fafb;
            transition: all 0.3s;
        }

        .test-item.running {
            border-left-color: #f59e0b;
            background: #fffbeb;
            animation: pulse 2s infinite;
        }

        .test-item.passed {
            border-left-color: #10b981;
            background: #ecfdf5;
        }

        .test-item.failed {
            border-left-color: #ef4444;
            background: #fef2f2;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.8; }
        }

        .test-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .test-name {
            font-size: 18px;
            font-weight: 600;
            color: #1f2937;
        }

        .test-status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }

        .test-status.running {
            background: #fef3c7;
            color: #92400e;
        }

        .test-status.passed {
            background: #d1fae5;
            color: #065f46;
        }

        .test-status.failed {
            background: #fee2e2;
            color: #991b1b;
        }

        .test-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }

        .metric {
            background: white;
            padding: 12px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }

        .metric-label {
            font-size: 12px;
            color: #6b7280;
            margin-bottom: 5px;
        }

        .metric-value {
            font-size: 20px;
            font-weight: 600;
            color: #111827;
        }

        .run-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 30px;
            cursor: pointer;
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
            transition: all 0.3s;
            margin-bottom: 20px;
        }

        .run-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.6);
        }

        .run-button:active {
            transform: translateY(0);
        }

        .run-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e5e7eb;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 15px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
        }

        .connection-status {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #10b981;
            margin-right: 8px;
            animation: blink 2s infinite;
        }

        .connection-status.disconnected {
            background: #ef4444;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .timestamp {
            font-size: 12px;
            color: #9ca3af;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 StackSense Live Testing Dashboard</h1>
            <p>
                <span class="connection-status" id="connection-status"></span>
                <span id="connection-text">Connecting...</span>
            </p>
        </div>

        <button class="run-button" id="run-tests-btn" onclick="runTests()">
            🚀 Run Test Suite
        </button>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Tests</div>
                <div class="stat-value" id="total-tests">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Passed</div>
                <div class="stat-value success" id="passed-tests">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Failed</div>
                <div class="stat-value error" id="failed-tests">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Latency</div>
                <div class="stat-value warning" id="avg-latency">0ms</div>
            </div>
        </div>

        <div class="tests-container">
            <h2 style="margin-bottom: 20px; color: #1f2937;">Test Results</h2>
            <div id="tests-list">
                <p style="color: #9ca3af; text-align: center; padding: 40px;">
                    Click "Run Test Suite" to start testing
                </p>
            </div>
        </div>
    </div>

    <script>
        let ws;
        let tests = {};
        let totalTests = 0;
        let passedTests = 0;
        let failedTests = 0;

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(protocol + '//' + window.location.host + '/ws');

            ws.onopen = () => {
                document.getElementById('connection-status').classList.remove('disconnected');
                document.getElementById('connection-text').textContent = 'Connected';
            };

            ws.onclose = () => {
                document.getElementById('connection-status').classList.add('disconnected');
                document.getElementById('connection-text').textContent = 'Disconnected - Reconnecting...';
                setTimeout(connectWebSocket, 3000);
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleUpdate(data);
            };
        }

        function handleUpdate(data) {
            if (data.type === 'test_start') {
                addOrUpdateTest(data.test_name, 'running', {});
            } else if (data.type === 'test_complete') {
                const result = data.result;
                addOrUpdateTest(result.test_name, result.status, result.metrics, result.duration_ms);

                // Update stats
                if (result.status === 'passed') {
                    passedTests++;
                } else if (result.status === 'failed') {
                    failedTests++;
                }

                updateStats();
            }
        }

        function addOrUpdateTest(testName, status, metrics, duration = 0) {
            tests[testName] = { status, metrics, duration };
            totalTests = Object.keys(tests).length;
            renderTests();
        }

        function renderTests() {
            const container = document.getElementById('tests-list');
            container.innerHTML = '';

            for (const [testName, data] of Object.entries(tests)) {
                const testItem = document.createElement('div');
                testItem.className = `test-item ${data.status}`;

                const statusBadge = `<span class="test-status ${data.status}">${data.status}</span>`;
                const durationText = data.duration > 0 ? `${data.duration.toFixed(1)}ms` : '';

                let metricsHTML = '';
                if (Object.keys(data.metrics).length > 0) {
                    metricsHTML = '<div class="test-metrics">';
                    for (const [key, value] of Object.entries(data.metrics)) {
                        metricsHTML += `
                            <div class="metric">
                                <div class="metric-label">${formatKey(key)}</div>
                                <div class="metric-value">${formatValue(value)}</div>
                            </div>
                        `;
                    }
                    metricsHTML += '</div>';
                }

                testItem.innerHTML = `
                    <div class="test-header">
                        <div class="test-name">${testName}</div>
                        <div>
                            ${statusBadge}
                            ${durationText ? `<span style="margin-left: 10px; color: #6b7280;">${durationText}</span>` : ''}
                        </div>
                    </div>
                    ${metricsHTML}
                `;

                container.appendChild(testItem);
            }
        }

        function formatKey(key) {
            return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        }

        function formatValue(value) {
            if (typeof value === 'number') {
                return value.toFixed(2);
            }
            return value;
        }

        function updateStats() {
            document.getElementById('total-tests').textContent = totalTests;
            document.getElementById('passed-tests').textContent = passedTests;
            document.getElementById('failed-tests').textContent = failedTests;

            // Calculate average latency
            let totalLatency = 0;
            let count = 0;
            for (const data of Object.values(tests)) {
                if (data.duration > 0) {
                    totalLatency += data.duration;
                    count++;
                }
            }
            const avgLatency = count > 0 ? totalLatency / count : 0;
            document.getElementById('avg-latency').textContent = avgLatency.toFixed(1) + 'ms';
        }

        async function runTests() {
            const btn = document.getElementById('run-tests-btn');
            btn.disabled = true;
            btn.textContent = '🔄 Running Tests...';

            // Reset state
            tests = {};
            totalTests = 0;
            passedTests = 0;
            failedTests = 0;
            updateStats();
            renderTests();

            try {
                const response = await fetch('/api/run-tests', { method: 'POST' });
                const data = await response.json();
                console.log('Tests started:', data);
            } catch (error) {
                console.error('Failed to start tests:', error);
                btn.textContent = '❌ Failed to Start';
                setTimeout(() => {
                    btn.disabled = false;
                    btn.textContent = '🚀 Run Test Suite';
                }, 3000);
            }

            // Re-enable button after tests complete (30s timeout)
            setTimeout(() => {
                btn.disabled = false;
                btn.textContent = '🚀 Run Test Suite Again';
            }, 30000);
        }

        // Connect on load
        connectWebSocket();
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn

    print("=" * 80)
    print("🧪 StackSense Live Testing Dashboard")
    print("=" * 80)
    print("\nStarting server...")
    print("Dashboard: http://localhost:8080")
    print("\nPress Ctrl+C to stop")
    print("=" * 80)

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
