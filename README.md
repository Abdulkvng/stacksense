# StackSense

AI Economic Intelligence Layer. StackSense goes beyond observability—it is an **AI Operating System** with runtime control over all LLM requests, automatically reducing spend, routing intelligently, and acting as a CFO for your AI infrastructure.
<<<<<<< Updated upstream
=======

## 🚀 AI Gateway - Runtime Control Layer

StackSense intercepts **every LLM request** before it reaches the provider and applies intelligent controls:

- **Dynamic Model Routing** - Switch between GPT-4 ↔ GPT-4o-mini based on quality needs
- **Vendor Switching** - Failover to different providers on latency spikes
- **Model Tier Dropping** - Automatically downgrade when quality threshold is met
- **Budget Blocking** - Hard stop requests that exceed budgets
- **Prompt Rewriting** - Reduce tokens while preserving meaning (15-30% savings)
- **Cost Simulation** - "What if" scenarios for different strategies
- **Monthly Prediction** - Forecast overruns before they happen
- **Auto-Throttling** - Prevent runaway agent costs with circuit breakers

📘 **[Read the AI Gateway Guide](AI_GATEWAY_GUIDE.md)** | 💻 **[See Integration Example](examples/gateway_integration_example.py)** | ⚡ **[Performance Guide](PERFORMANCE.md)** | ✅ **[Production Readiness](PRODUCTION_READINESS.md)**

### ⚡ Performance

| Version | Latency | Throughput | Overhead |
|---------|---------|------------|----------|
| Async Gateway | 2-6ms | 500 req/s | < 0.5% |
| Async + Redis | 1-3ms | 1000+ req/s | < 0.2% |
| Cache Hit | < 1ms | - | 100x faster |

**Compared to LLM latency (1500-3000ms), gateway adds negligible overhead while saving 25-35% on costs.**
>>>>>>> Stashed changes

## Supported Providers

| Provider | Auto-detect | Token Tracking | Cost Calculation |
|----------|-------------|----------------|------------------|
| OpenAI (GPT-4o, o1, o3) | Yes | Yes | Yes |
| Anthropic (Claude 4, 3.5) | Yes | Yes | Yes |
| Google Gemini (2.0, 1.5) | Yes | Yes | Yes |
| Mistral | Yes | Yes | Yes |
| Cohere (Command R) | Yes | Yes | Yes |
| DeepSeek | Yes | Yes | Yes |
| ElevenLabs | Yes | Characters | Yes |
| Pinecone | Yes | Queries | Yes |

## AI Gateway - Runtime Control Layer

StackSense intercepts **every LLM request** before it reaches the provider and applies intelligent controls:

- **Dynamic Model Routing** - Switch between GPT-4 and GPT-4o-mini based on quality needs
- **Vendor Switching** - Failover to different providers on latency spikes
- **Model Tier Dropping** - Automatically downgrade when quality threshold is met
- **Budget Blocking** - Hard stop requests that exceed budgets
- **Prompt Rewriting** - Reduce tokens while preserving meaning (15-30% savings)
- **Cost Simulation** - "What if" scenarios for different strategies
- **Monthly Prediction** - Forecast overruns before they happen
- **Auto-Throttling** - Prevent runaway agent costs with circuit breakers

### Performance

| Version | Latency | Throughput | Overhead |
|---------|---------|------------|----------|
| Async Gateway | 2-6ms | 500 req/s | < 0.5% |
| Async + Redis | 1-3ms | 1000+ req/s | < 0.2% |
| Cache Hit | < 1ms | - | 100x faster |

## Quick Start

### Installation

```bash
pip install stacksense
```

### Basic Usage

```python
from stacksense import StackSense
import openai

# Initialize StackSense
ss = StackSense(api_key="your_key")

# Monitor your OpenAI client - works with any supported provider
client = ss.monitor(openai.OpenAI())

# All API calls are automatically tracked
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Get metrics
metrics = ss.get_metrics(timeframe="24h")
print(f"Total cost: ${metrics['total_cost']}")
```

<<<<<<< Updated upstream
### Multi-Provider Monitoring

```python
from stacksense import StackSense
import openai
import anthropic

ss = StackSense()

# Monitor multiple providers simultaneously
oai = ss.monitor(openai.OpenAI())
claude = ss.monitor(anthropic.Anthropic())

# Both are tracked with provider-specific token extraction
oai.chat.completions.create(model="gpt-4o", messages=[...])
claude.messages.create(model="claude-sonnet-4-20250514", messages=[...])

# Unified cost breakdown across all providers
print(ss.get_cost_breakdown())
```

### Decorator API

Track any function without wrapping a client:

```python
import stacksense

@stacksense.track(provider="openai", model="gpt-4o")
def my_ai_call(prompt):
    return openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )

# Async functions work too
@stacksense.track(provider="anthropic", model="claude-sonnet-4-20250514")
async def my_async_call(prompt):
    return await anthropic_client.messages.create(...)
```

### Framework Middleware

#### FastAPI

```python
from fastapi import FastAPI
from stacksense import StackSense
from stacksense.middleware import FastAPIMiddleware

app = FastAPI()
ss = StackSense()
app.add_middleware(FastAPIMiddleware, stacksense=ss)
```

#### Flask

```python
from flask import Flask
from stacksense import StackSense
from stacksense.middleware import FlaskMiddleware

app = Flask(__name__)
ss = StackSense()
FlaskMiddleware(app, stacksense=ss)
```

#### Django

```python
# settings.py
MIDDLEWARE = [
    ...
    'stacksense.middleware.DjangoMiddleware',
]
```

### AI Gateway Usage

Intercept and control all LLM requests:

```python
from stacksense.gateway import AIGateway

=======
### AI Gateway Usage

Intercept and control all LLM requests with the AI Gateway:

```python
from stacksense.gateway import AIGateway
import openai

# Initialize gateway with runtime controls
>>>>>>> Stashed changes
gateway = AIGateway(
    db_session=db_session,
    user_id=user_id,
    enable_cache=True,
    enable_optimization=True,
    enable_smart_routing=True
)

messages = [{"role": "user", "content": "Explain quantum computing"}]

<<<<<<< Updated upstream
intercepted = gateway.intercept(
    messages=messages,
    model="gpt-4",
    max_latency_ms=2000,
    min_quality_score=0.80
)

if "error" not in intercepted:
    response = openai.chat.completions.create(
        model=intercepted["model"],
        messages=intercepted["messages"]
    )
```

### Alerts & Webhooks

```python
from stacksense.alerts import AlertManager, AlertRule

alerts = AlertManager(tracker=ss.tracker)

# Alert when hourly cost exceeds $5
alerts.add_rule(AlertRule(
    name="High cost alert",
    metric="cost",
    threshold=5.0,
    window="1h",
    cooldown="15m",
))

# Alert on high error rate
alerts.add_rule(AlertRule(
    name="Error spike",
    metric="error_rate",
    threshold=10.0,
    window="1h",
))

# Send alerts to Slack
alerts.add_webhook("https://hooks.slack.com/services/...")

# Check alerts (call periodically)
triggered = alerts.check()
```

### Export Data

```python
from stacksense.exporters import Exporter

exporter = Exporter(ss.tracker)

# Export to CSV or JSON
exporter.to_csv("metrics.csv")
exporter.to_json("metrics.json", include_summary=True)

# Get as dictionary (useful for APIs)
data = exporter.to_dict()
```

### CLI

```bash
# Launch dashboard
stacksense dashboard --port 5000

# View current metrics
stacksense status

# Export data
stacksense export csv -o metrics.csv
stacksense export json -o metrics.json

# Database management
stacksense db init
stacksense db health
```
=======
# Intercept request before sending to LLM
intercepted = gateway.intercept(
    messages=messages,
    model="gpt-4",
    max_latency_ms=2000,  # Switch provider if slow
    min_quality_score=0.80  # Drop tier if quality met
)

# Check if allowed
if "error" in intercepted:
    print(f"Blocked: {intercepted['message']}")
else:
    # Execute with potentially modified model/messages
    response = openai.ChatCompletion.create(
        model=intercepted["model"],  # May be downgraded
        messages=intercepted["messages"]  # May be optimized
    )

    # Track performance (enables learning)
    gateway.post_execution_tracking(
        request=intercepted,
        response=response,
        actual_cost=0.002,
        latency=1200
    )
```

**What the Gateway does:**
1. ✅ Checks budget and throttling limits
2. ✂️ Optimizes prompts to reduce tokens (15-30% savings)
3. 💾 Returns cached responses for identical queries
4. 🔀 Routes to best provider based on latency/cost/quality
5. 📊 Tracks quality for future tier recommendations

📘 **[Full AI Gateway Guide](AI_GATEWAY_GUIDE.md)** with cost prediction, quality tracking, and more.
>>>>>>> Stashed changes

## Database Support

Built-in persistence with SQLite (default) and PostgreSQL:

```bash
# SQLite (default - no setup required)
# Data stored in ./stacksense.db

# PostgreSQL (production)
pip install stacksense[postgresql]
export STACKSENSE_DB_URL="postgresql://user:pass@host:5432/stacksense"
```

See [docs/DATABASE_GUIDE.md](docs/DATABASE_GUIDE.md) for detailed database configuration.

## Configuration

### Environment Variables

```bash
STACKSENSE_API_KEY=your_api_key
STACKSENSE_PROJECT_ID=your_project_id
STACKSENSE_ENABLE_DB=true
STACKSENSE_DB_URL=sqlite:///stacksense.db
STACKSENSE_DB_ECHO=false
STACKSENSE_ENVIRONMENT=production
STACKSENSE_DEBUG=false
```

## Docker Deployment

```bash
docker-compose up -d
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete deployment guide.

## Documentation

<<<<<<< Updated upstream
- [docs/AI_GATEWAY_GUIDE.md](docs/AI_GATEWAY_GUIDE.md) - AI Gateway runtime control layer
- [docs/TELEMETRY_GUIDE.md](docs/TELEMETRY_GUIDE.md) - Telemetry and monitoring guide
=======
- **[AI_GATEWAY_GUIDE.md](AI_GATEWAY_GUIDE.md)** - AI Gateway runtime control layer
- **[TELEMETRY_GUIDE.md](TELEMETRY_GUIDE.md)** - Complete telemetry and monitoring guide
- [docs/QUICKSTART.md](docs/QUICKSTART.md) - Quick start guide
>>>>>>> Stashed changes
- [docs/DATABASE_GUIDE.md](docs/DATABASE_GUIDE.md) - Database setup and usage
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Production deployment
- [docs/QUICKSTART.md](docs/QUICKSTART.md) - Quick start guide
- [CHANGELOG.md](CHANGELOG.md) - Version history

## Development

```bash
# Clone and install
git clone https://github.com/Abdulkvng/stacksense.git
cd stacksense
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Format and lint
black stacksense/
isort stacksense/
flake8 stacksense/

# Pre-commit hooks
pip install pre-commit
pre-commit install
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

Abdulrahman Sadiq - abdulkvng@gmail.com
