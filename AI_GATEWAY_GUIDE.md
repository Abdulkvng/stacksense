# StackSense AI Gateway - Runtime Control Layer

Transform StackSense from observability to an **AI Operating System** with runtime control over all LLM requests.

## 🚀 What is the AI Gateway?

The AI Gateway intercepts **every LLM request** before it reaches the provider and applies intelligent controls:

### ⚡ Performance Characteristics

| Version | Latency (P50) | Throughput | Best For |
|---------|---------------|------------|----------|
| **Sync Gateway** | 8-15ms | 125 req/s | Simple apps, low traffic |
| **Async Gateway** | 2-6ms | 500 req/s | Production, medium traffic |
| **Async + Redis** | 1-3ms | 1000+ req/s | High scale, distributed |

**Compared to LLM latency (1500-3000ms), gateway adds < 1% overhead.**

📊 **[See Performance Benchmarks](PERFORMANCE.md)**

- **Dynamic Model Routing** - Switch between GPT-4 ↔ GPT-4o-mini based on quality needs
- **Vendor Switching** - Failover to different providers on latency spikes
- **Model Tier Dropping** - Automatically downgrade when quality threshold is met
- **Budget Blocking** - Hard stop requests that exceed budgets
- **Prompt Rewriting** - Reduce tokens while preserving meaning
- **Cost Simulation** - "What if" scenarios for different strategies
- **Monthly Prediction** - Forecast overruns before they happen
- **Auto-Throttling** - Prevent runaway agent costs

## 📦 Architecture

```
Your App → AI Gateway → LLM Provider
              ↓
        [Intercept Pipeline]
        1. Throttling Check
        2. Budget Check
        3. Prompt Optimization
        4. Cache Lookup
        5. Smart Routing
        6. Execution
        7. Quality Tracking
        8. Cache Storage
```

## 🔧 Quick Start

### Production-Ready Async Gateway (Recommended)

For production use with minimal latency overhead:

```python
import asyncio
from stacksense.gateway import AsyncAIGateway
import redis.asyncio as redis

async def main():
    # Connect to Redis for ultra-fast caching (1-2ms)
    redis_client = await redis.from_url("redis://localhost:6379/0")

    # Initialize async gateway
    gateway = AsyncAIGateway(
        db_session=db_session,
        user_id=user_id,
        redis_client=redis_client,  # Optional but recommended
        enable_cache=True,
        enable_optimization=True,
        enable_smart_routing=True,
        fail_open=True  # Never block production
    )

    # Intercept request (runs all checks in parallel)
    intercepted = await gateway.intercept(
        messages=messages,
        model="gpt-4",
        max_latency_ms=2000,
        min_quality_score=0.80
    )

    # Check for errors
    if "error" in intercepted:
        print(f"Blocked: {intercepted['message']}")
        return

    # Execute with potentially modified model/messages
    response = await openai_client.chat.completions.create(
        model=intercepted["model"],
        messages=intercepted["messages"]
    )

    # Track performance (background task)
    await gateway.post_execution_tracking(
        request=intercepted,
        response=response,
        actual_cost=0.002,
        latency=1200
    )

asyncio.run(main())
```

**Performance**: 1-6ms overhead (< 0.5% of LLM latency)

### Basic Usage (Sync)

```python
from stacksense.gateway import AIGateway

# Initialize gateway
gateway = AIGateway(
    db_session=db_session,
    user_id=user_id,
    enable_cache=True,
    enable_optimization=True,
    enable_smart_routing=True
)

# Intercept request
messages = [
    {"role": "user", "content": "Explain quantum computing"}
]

result = gateway.intercept(
    messages=messages,
    model="gpt-4",
    max_latency_ms=2000,  # Switch provider if slow
    min_quality_score=0.80  # Drop tier if quality met
)

# Result contains:
# - model: Selected model (may differ from requested)
# - messages: Optimized messages (may be compressed)
# - optimized: Whether prompt was optimized
# - from_cache: Whether served from cache
# - budget_action: "allow", "downgrade", or "block"
```

### With OpenAI Client

```python
from stacksense.gateway import AIGateway
import openai

gateway = AIGateway(db_session=db_session, user_id=user_id)

messages = [{"role": "user", "content": "Write a function to check if a number is prime"}]

# Intercept before sending
intercepted = gateway.intercept(messages=messages, model="gpt-4")

if "error" in intercepted:
    # Budget exceeded or throttled
    print(f"Request blocked: {intercepted['message']}")
else:
    # Execute with potentially modified model/messages
    response = openai.ChatCompletion.create(
        model=intercepted["model"],
        messages=intercepted["messages"]
    )

    # Track quality after execution
    gateway.post_execution_tracking(
        request=intercepted,
        response=response,
        actual_cost=0.002,
        latency=1200
    )
```

## 🎯 Core Components

### 1. Smart Router

**Real-time provider selection** based on latency, cost, and quality.

```python
from stacksense.gateway import SmartRouter

router = SmartRouter(db_session=db_session, user_id=user_id)

# Select best provider
selection = router.select_provider(
    model="gpt-4",
    messages=messages,
    context={"max_latency_ms": 2000}
)

# selection = {
#     "provider": "anthropic",
#     "model": "claude-3-opus",
#     "switched": True,
#     "reason": "latency_spike_2500ms",
#     "estimated_latency": 800,
#     "estimated_cost": 0.0015
# }

# Record performance for learning
router.record_performance(
    provider="openai",
    model="gpt-4",
    latency=2500,
    success=True,
    cost=0.003
)
```

**Routing Decisions:**
- **Latency Spike**: Switch to fastest alternative if avg latency > threshold
- **Quality Threshold**: Drop to cheaper tier if quality requirement met
- **Provider Health**: Failover if error rate > 10%

### 2. Prompt Optimizer

**Token efficiency** through intelligent compression.

```python
from stacksense.gateway import PromptOptimizer

optimizer = PromptOptimizer(aggressive_mode=False)

messages = [
    {"role": "user", "content": "Could you please actually just explain what a prime number is?"}
]

result = optimizer.optimize(messages, model="gpt-4", target_reduction=0.15)

# result = {
#     "optimized": True,
#     "original_tokens": 150,
#     "optimized_tokens": 120,
#     "savings_percent": 20.0,
#     "messages": [{"role": "user", "content": "Explain what a prime number is"}]
# }
```

**Optimization Techniques:**
- Removes filler words (actually, basically, just, etc.)
- Compresses verbose phrases ("in order to" → "to")
- Removes redundant punctuation
- Preserves semantic meaning

**Context Compression:**
```python
# Truncate conversation history to fit token limit
compressed = optimizer.compress_context(
    messages=long_conversation,
    max_tokens=4000
)
# Keeps: system prompt + recent messages + last user input
```

### 3. Cost Predictor

**Monthly forecasting** and budget overrun detection.

```python
from stacksense.gateway import CostPredictor

predictor = CostPredictor(db_session=db_session, user_id=user_id)

# Predict end-of-month cost
prediction = predictor.predict_monthly_cost(
    current_spend=250.0,
    days_elapsed=15,
    days_in_month=30
)

# prediction = {
#     "predicted_monthly_cost": 520.0,
#     "projection_method": "trend_adjusted_acceleration",
#     "confidence": 0.7,
#     "daily_average": 16.67,
#     "trend": "accelerating"
# }

# Check for budget overrun
overrun = predictor.check_budget_overrun(
    current_spend=250.0,
    monthly_budget=400.0,
    days_elapsed=15
)

# overrun = {
#     "will_exceed": True,
#     "predicted_cost": 520.0,
#     "overage": 120.0,
#     "overage_percent": 30.0,
#     "days_until_exceeded": 5,
#     "recommended_action": "enable_cost_controls"
# }

# Simulate scenarios
scenario = predictor.simulate_scenario(
    scenario={
        "model_switch": {"from": "gpt-4", "to": "gpt-4o-mini"},
        "optimization_enabled": True,
        "rate_reduction": 0.2  # 20% fewer requests
    },
    current_spend=250.0,
    days_elapsed=15
)

# scenario = {
#     "projected_cost": 180.0,
#     "savings": 340.0,
#     "savings_percent": 65.4,
#     "scenario_description": "Scenario: switch gpt-4 → gpt-4o-mini, enable optimization, reduce rate by 20%"
# }
```

### 4. Request Throttler

**Auto-throttling** with circuit breakers.

```python
from stacksense.gateway import RequestThrottler

throttler = RequestThrottler(db_session=db_session, user_id=user_id)

# Set custom limits
throttler.set_limits(
    requests_per_minute=50,
    cost_per_minute=0.5  # $0.50/min
)

# Check request
check = throttler.check_request(
    scope="feature_chat",
    estimated_cost=0.02,
    agent_id="data_pipeline",
    request_hash="abc123..."
)

# check = {
#     "allowed": True,
#     "reason": "ok",
#     "retry_after": 0,
#     "current_rate": 23,
#     "limit": 50
# }

# Record provider failures
throttler.record_failure("provider_openai")  # Opens circuit after 5 failures

# Record success (resets failures)
throttler.record_success("provider_openai")
```

**Circuit Breaker States:**
- **CLOSED**: Normal operation
- **OPEN**: Provider failing, block all requests (60s)
- **HALF_OPEN**: Testing if provider recovered

**Agent Loop Detection:**
Prevents infinite loops by detecting same request 3+ times within 10 seconds.

### 5. Semantic Cache

**Intelligent caching** with TTL and LRU eviction.

```python
from stacksense.gateway import SemanticCache

cache = SemanticCache(max_size=1000, default_ttl=3600)

messages = [{"role": "user", "content": "What is 2+2?"}]

# Generate cache key
cache_key = cache.generate_key(messages, model="gpt-4")

# Check cache
cached_response = cache.get(cache_key)

if cached_response:
    print("Cache hit!")
else:
    # Make API call
    response = call_llm(messages)

    # Store in cache
    cache.set(cache_key, response, ttl=3600)

# Get statistics
stats = cache.get_stats()
# stats = {
#     "size": 342,
#     "max_size": 1000,
#     "hits": 1523,
#     "misses": 892,
#     "hit_rate": 0.63,
#     "evictions": 15,
#     "total_requests": 2415
# }
```

### 6. Quality Tracker

**Auto-tier selection** based on quality metrics.

```python
from stacksense.gateway import QualityTracker

tracker = QualityTracker(db_session=db_session, user_id=user_id)

# Track response quality
tracker.track_response(
    model="gpt-4",
    response="A prime number is...",
    cost=0.003,
    latency=1200,
    error=False,
    user_feedback=0.95  # Optional user rating
)

# Get model quality
quality = tracker.get_model_quality("gpt-4")
# quality = {
#     "avg_quality": 0.92,
#     "quality_rating": "excellent",
#     "response_count": 1523,
#     "error_rate": 0.02,
#     "avg_latency": 1350,
#     "cost_per_response": 0.0028,
#     "cost_per_quality": 0.00304
# }

# Get downgrade recommendation
recommendation = tracker.recommend_tier_downgrade(
    current_model="gpt-4",
    min_quality_threshold=0.85
)

# recommendation = {
#     "recommended_model": "gpt-4o",
#     "current_quality": 0.92,
#     "recommended_quality": 0.89,
#     "quality_delta": -0.03,
#     "cost_savings": 83.3,  # 83% cheaper
#     "current_cost": 0.003,
#     "recommended_cost": 0.0005
# }

# Get quality leaderboard
leaderboard = tracker.get_quality_leaderboard()
# [
#     {"model": "gpt-4o-mini", "avg_quality": 0.87, "cost_per_quality": 0.0002},
#     {"model": "gpt-4o", "avg_quality": 0.90, "cost_per_quality": 0.0006},
#     {"model": "gpt-4", "avg_quality": 0.92, "cost_per_quality": 0.0030}
# ]
```

## 🎮 Complete Integration Example

```python
from stacksense.gateway import AIGateway
import openai

# Initialize gateway with all features
gateway = AIGateway(
    db_session=db_session,
    user_id=user_id,
    enable_cache=True,
    enable_optimization=True,
    enable_smart_routing=True
)

def chat_with_ai(messages, model="gpt-4"):
    """
    Chat with AI through StackSense Gateway.

    Automatically handles:
    - Budget enforcement
    - Prompt optimization
    - Caching
    - Smart routing
    - Quality tracking
    """

    # Step 1: Intercept request
    intercepted = gateway.intercept(
        messages=messages,
        model=model,
        max_latency_ms=2000,
        min_quality_score=0.80
    )

    # Step 2: Check if blocked/throttled
    if "error" in intercepted:
        return {
            "error": True,
            "message": intercepted["message"],
            "retry_after": intercepted.get("retry_after")
        }

    # Step 3: Check cache hit
    if intercepted.get("from_cache"):
        return {
            "response": intercepted["response"],
            "cached": True,
            "cost": 0.0
        }

    # Step 4: Execute with potentially modified model/messages
    import time
    start_time = time.time()

    response = openai.ChatCompletion.create(
        model=intercepted["model"],
        messages=intercepted["messages"]
    )

    latency = (time.time() - start_time) * 1000  # Convert to ms

    # Step 5: Track performance
    actual_cost = calculate_cost(response)

    gateway.post_execution_tracking(
        request=intercepted,
        response=response,
        actual_cost=actual_cost,
        latency=latency
    )

    return {
        "response": response,
        "cached": False,
        "cost": actual_cost,
        "model_used": intercepted["model"],
        "model_switched": intercepted.get("model") != model,
        "prompt_optimized": intercepted.get("optimized", False)
    }

# Usage
result = chat_with_ai(
    messages=[{"role": "user", "content": "Explain machine learning"}],
    model="gpt-4"
)

if result.get("error"):
    print(f"Request blocked: {result['message']}")
else:
    print(f"Response: {result['response']}")
    print(f"Cost: ${result['cost']:.4f}")
    print(f"Cached: {result['cached']}")
    if result["model_switched"]:
        print(f"Model switched to: {result['model_used']}")
```

## 🔄 Workflow Examples

### Budget-Aware Auto-Downgrade

```python
# Set budget in database
budget_enforcer.set_budget(
    scope="global",
    limit=100.0,
    period="monthly"
)

# Request will auto-downgrade if budget at risk
result = gateway.intercept(
    messages=messages,
    model="gpt-4"  # May become gpt-4o-mini
)

# result["budget_action"] = "downgrade"
# result["model"] = "gpt-4o-mini"
```

### Latency-Triggered Provider Switch

```python
# Record high latency for OpenAI
smart_router.record_performance(
    provider="openai",
    model="gpt-4",
    latency=3000,  # 3 seconds
    success=True,
    cost=0.003
)

# Next request automatically switches
result = gateway.intercept(
    messages=messages,
    model="gpt-4",
    max_latency_ms=2000  # 2 second threshold
)

# result["provider"] = "anthropic"
# result["model"] = "claude-3-opus"
# result["switched"] = True
# result["reason"] = "latency_spike_3000ms"
```

### Cost Prediction & Alerts

```python
predictor = CostPredictor(db_session=db_session, user_id=user_id)

# Check daily
overrun = predictor.check_budget_overrun(
    current_spend=get_month_to_date_spend(),
    monthly_budget=500.0,
    days_elapsed=get_days_elapsed()
)

if overrun["will_exceed"]:
    send_alert(
        f"Budget overrun predicted: ${overrun['predicted_cost']:.2f} > ${overrun['budget']:.2f}"
        f"\nRecommended action: {overrun['recommended_action']}"
    )
```

## 📊 Monitoring Gateway Performance

### Cache Statistics

```python
cache = gateway.cache
stats = cache.get_stats()

print(f"Cache hit rate: {stats['hit_rate']*100:.1f}%")
print(f"Cache size: {stats['size']}/{stats['max_size']}")
print(f"Total savings: ${stats['hits'] * 0.002:.2f}")  # Estimate
```

### Quality Metrics

```python
tracker = gateway.quality_tracker
all_metrics = tracker.get_all_metrics()

for model, metrics in all_metrics.items():
    print(f"{model}:")
    print(f"  Quality: {metrics['avg_quality']:.2f} ({metrics['quality_rating']})")
    print(f"  Cost/Quality: ${metrics['cost_per_quality']:.4f}")
    print(f"  Error Rate: {metrics['error_rate']*100:.1f}%")
```

### Throttling Status

```python
throttler = gateway.throttler
limits = throttler.get_current_limits(scope="global")

print(f"Requests/min: {limits['requests_per_minute']['current']}/{limits['requests_per_minute']['limit']}")
print(f"Cost/min: ${limits['cost_per_minute']['current']:.2f}/${limits['cost_per_minute']['limit']:.2f}")
```

## 🎯 Best Practices

1. **Enable All Features**: Cache, optimization, and smart routing work best together
2. **Set Conservative Budgets**: Use budget enforcement to prevent overruns
3. **Monitor Quality**: Regularly check quality metrics to validate tier downgrades
4. **Use Cost Prediction**: Run daily to catch overruns early
5. **Track Everything**: Post-execution tracking enables learning
6. **Test Scenarios**: Use cost simulator before making changes
7. **Set Throttling Limits**: Prevent runaway agent costs

## 🚨 Common Patterns

### Pattern 1: Cost-Optimized Chat

```python
result = gateway.intercept(
    messages=messages,
    model="gpt-4",
    min_quality_score=0.75  # Low threshold = more downgrades
)
```

### Pattern 2: Latency-Sensitive

```python
result = gateway.intercept(
    messages=messages,
    model="gpt-4",
    max_latency_ms=1000  # Aggressive switching
)
```

### Pattern 3: Quality-First

```python
result = gateway.intercept(
    messages=messages,
    model="gpt-4",
    min_quality_score=0.95  # High threshold = fewer downgrades
)
```

## 📈 Next Steps

1. Integrate gateway into your application
2. Configure budgets and limits
3. Monitor cost predictions
4. Enable auto-downgrade based on quality
5. Set up alerts for budget overruns
6. Analyze quality leaderboard
7. Optimize based on cost-per-quality metrics

---

**StackSense AI Gateway** - Transform observability into runtime control. 🚀
