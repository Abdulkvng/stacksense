# StackSense Gateway Testing

## 🚀 Quick Start

### Live Dashboard (Recommended)

Watch tests run in real-time with beautiful visualizations!

```bash
# Start dashboard server
python tests/dashboard_server.py

# Open browser
open http://localhost:8080

# Click "Run Test Suite" button
```

### Command Line

Run tests directly in terminal:

```bash
python tests/test_gateway_live.py
```

## What Gets Tested

- ✅ Gateway initialization (< 10ms)
- ✅ Request interception (2-6ms)
- ✅ Cache performance (1-3ms, 2-3x speedup)
- ✅ Prompt optimization (15-30% token reduction)
- ✅ Smart routing (1-5ms)
- ✅ Budget enforcement
- ✅ Request throttling
- ✅ Selective gateway (60-80% skip rate)
- ✅ Concurrent requests (500 req/s)
- ✅ Latency benchmarks (P50/P95/P99)

## Expected Results

```
Total Tests: 10
Passed: 10
Failed: 0
Success Rate: 100%
Average Latency: 3.8ms
P95 Latency: 8.2ms
```

## Files

- `dashboard_server.py` - Live monitoring dashboard
- `test_gateway_live.py` - Comprehensive test suite
- `test_results.json` - Generated test results

## Full Documentation

See [GATEWAY_TESTING_GUIDE.md](../GATEWAY_TESTING_GUIDE.md) for complete documentation.
