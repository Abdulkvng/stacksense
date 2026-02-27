# 🧪 StackSense Live Testing Environment

Complete testing environment with live dashboard, real-time metrics, and performance monitoring for the AI Gateway.

## 🚀 Quick Start (3 Steps)

###Step 1: Start the Dashboard Server

```bash
cd /Users/kvng/projects/stacksense
python tests/dashboard_server.py
```

### Step 2: Open the Dashboard

```bash
open http://localhost:8080
```

### Step 3: Run Tests

Click the **"🚀 Run Test Suite"** button and watch the magic happen! ✨

## 🎬 What You'll See

### Live Dashboard Features

1. **Real-Time Updates** via WebSocket
   - Tests run live in front of your eyes
   - Status changes: Running → Passed/Failed
   - Metrics stream in real-time

2. **Beautiful Visualizations**
   - Summary cards (Total, Passed, Failed, Avg Latency)
   - Color-coded test results
   - Individual test metrics
   - Progress animations

3. **Comprehensive Metrics**
   - Latency (P50, P95, P99)
   - Throughput (req/s)
   - Cache hit rates
   - Cost savings
   - Token reduction

## 📊 Tests Included

### 1. Gateway Initialization (< 10ms)
Tests component loading and resource allocation.

### 2. Basic Interception (2-6ms)
Tests request routing and message processing.

### 3. Cache Performance (1-3ms)
Measures cache hit vs miss speedup.

### 4. Prompt Optimization (15-30% reduction)
Tests token reduction and compression.

### 5. Smart Routing (1-5ms)
Tests provider selection and model tier dropping.

### 6. Budget Enforcement (1ms)
Tests spend tracking and budget limits.

### 7. Request Throttling (< 1ms)
Tests rate limiting and circuit breakers.

### 8. Selective Gateway (60-80% skip)
Tests cheap model detection and skip rate.

### 9. Concurrent Requests (100 concurrent)
Tests throughput with parallel execution.

### 10. Latency Benchmark (1000 iterations)
Comprehensive latency analysis with percentiles.

## 📈 Sample Results

```
================================================================================
TEST SUITE SUMMARY
================================================================================

📊 Overall Results:
   Total Tests: 10
   ✅ Passed: 10
   ❌ Failed: 0
   Success Rate: 100.0%
   Total Duration: 4127.3ms

⚡ Performance Metrics:
   Average Latency: 3.82ms
   Median Latency: 3.10ms
   P95 Latency: 8.15ms
   P99 Latency: 12.34ms

================================================================================
✅ Test Suite Complete!
================================================================================
```

## 🎯 What Gets Validated

### Performance
- ✅ Gateway overhead < 6ms (P50)
- ✅ Gateway overhead < 15ms (P95)
- ✅ Throughput > 400 req/s
- ✅ Cache speedup > 2x

### Efficiency
- ✅ Token reduction > 15%
- ✅ Cache hit rate > 50%
- ✅ Skip rate > 60% (selective gateway)
- ✅ Cost savings > 20%

### Reliability
- ✅ Success rate: 100%
- ✅ Error rate: 0%
- ✅ Circuit breakers working
- ✅ Budget enforcement active

## 🎨 Dashboard Screenshot

```
┌──────────────────────────────────────────────────────────────────────┐
│  🧪 StackSense Live Testing Dashboard                                │
│  ● Connected                                                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  [🚀 Run Test Suite]                                                 │
│                                                                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │
│  │ Total Tests│  │   Passed   │  │   Failed   │  │Avg Latency │    │
│  │     10     │  │      9     │  │      1     │  │   3.8ms    │    │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │
│                                                                        │
│  Test Results                                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ✅ Gateway Initialization                       PASSED 8.2ms  │   │
│  │    • init_time_ms: 8.2                                        │   │
│  │    • components_loaded: 6                                     │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │ ✅ Basic Request Interception                   PASSED 4.3ms  │   │
│  │    • latency_ms: 4.3                                          │   │
│  │    • intercepted: true                                        │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │ ✅ Cache Hit Performance                        PASSED 1.8ms  │   │
│  │    • cache_hit_latency_ms: 1.8                                │   │
│  │    • speedup: 2.5x                                            │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │ 🔄 Concurrent Requests (100)                    RUNNING...    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

## 🛠️ Command Line Alternative

Don't want the dashboard? Run tests directly:

```bash
python tests/test_gateway_live.py
```

Output goes to terminal + `test_results.json`

## 🔧 Customization

### Add Custom Test

```python
# In test_gateway_live.py

async def test_my_feature(self) -> Dict:
    """Test my custom feature."""
    # Your test logic
    return {"metric": value}

# In run_all_tests()
await self.run_test("My Test", self.test_my_feature)
```

### Change Parameters

```python
# More concurrent requests
await self.run_test(
    "Concurrent Requests (1000 concurrent)",
    self.test_concurrent_requests,
    concurrency=1000  # Changed from 100
)

# More iterations
await self.run_test(
    "Latency Benchmark (10000 iterations)",
    self.test_latency_benchmark,
    iterations=10000  # Changed from 1000
)
```

## 🐛 Troubleshooting

### Dashboard Won't Load

```bash
# Check if server is running
ps aux | grep dashboard_server

# Check port 8080
lsof -i :8080

# Use different port (edit dashboard_server.py)
uvicorn.run(app, host="0.0.0.0", port=8081)
```

### WebSocket Disconnected

The dashboard auto-reconnects. If issues persist:
- Check firewall
- Try different browser
- Disable proxy

### Import Errors

```bash
# Ensure correct directory
cd /Users/kvng/projects/stacksense

# Install deps
pip install fastapi uvicorn websockets

# Add to PYTHONPATH
export PYTHONPATH=$(pwd):$PYTHONPATH
```

## 📊 Understanding Results

### Status Indicators

| Icon | Status | Color | Meaning |
|------|--------|-------|---------|
| 🔄 | Running | Orange | Currently executing |
| ✅ | Passed | Green | Completed successfully |
| ❌ | Failed | Red | Error occurred |

### Benchmark Targets

| Metric | Target | Excellent | Investigate |
|--------|--------|-----------|-------------|
| P50 Latency | < 5ms | < 3ms | > 10ms |
| P95 Latency | < 15ms | < 10ms | > 30ms |
| Cache Hit Rate | > 50% | > 70% | < 30% |
| Token Reduction | > 15% | > 25% | < 10% |
| Success Rate | 100% | 100% | < 90% |

## 📁 Output Files

### test_results.json

Complete test results in JSON format:

```json
{
  "summary": {
    "total": 10,
    "passed": 10,
    "failed": 0,
    "duration_ms": 4127.3
  },
  "results": [...]
}
```

Use this for:
- CI/CD integration
- Automated reporting
- Historical comparison
- Performance tracking

## 🎯 Next Steps

1. ✅ Run `python tests/dashboard_server.py`
2. ✅ Open http://localhost:8080
3. ✅ Click "Run Test Suite"
4. ✅ Watch tests execute live
5. ✅ Analyze metrics and results
6. ✅ Customize for your needs

---

**🎉 You now have a complete live testing environment with real-time monitoring!**
