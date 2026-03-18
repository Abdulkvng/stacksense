<p align="center">
  <a href="https://github.com/Abdulkvng/stacksense">
    <img src="banner.svg" alt="StackSense — Know exactly what your AI costs" width="100%">
  </a>
</p>

<p align="center">
  <a href="https://pypi.org/project/stacksense/"><img src="https://img.shields.io/pypi/v/stacksense.svg?style=flat-square" alt="PyPI version"></a>
  <a href="https://github.com/Abdulkvng/stacksense/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License"></a>
  <a href="https://pypi.org/project/stacksense/"><img src="https://img.shields.io/pypi/pyversions/stacksense.svg?style=flat-square" alt="Python versions"></a>
  <img src="https://komarev.com/ghpvc/?username=Abdulkvng&repo=stacksense&label=views&color=6366f1&style=flat-square" alt="Profile views">
</p>

<p align="center">
  <a href="#getting-started">Getting Started</a>&nbsp;&nbsp;·&nbsp;&nbsp;
  <a href="#providers">Providers</a>&nbsp;&nbsp;·&nbsp;&nbsp;
  <a href="#features">Features</a>&nbsp;&nbsp;·&nbsp;&nbsp;
  <a href="#documentation">Documentation</a>&nbsp;&nbsp;·&nbsp;&nbsp;
  <a href="#contributing">Contributing</a>
</p>

<br/>

## Getting Started

```bash
pip install stacksense
```

```python
from stacksense import StackSense
import openai

ss = StackSense()
client = ss.monitor(openai.OpenAI())

# Use client exactly as before — every call is now tracked
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(ss.get_metrics())
# {'total_calls': 1, 'total_tokens': 28, 'total_cost': 0.0004, ...}
```

No config files. No dashboard setup. Just `monitor()` and go.

## The Problem

You're shipping AI features. Costs are climbing. You have no idea which endpoint, which model, or which user is burning through your budget.

```
Month 1:  $12 in API costs. No big deal.
Month 3:  $480. Wait, what?
Month 5:  $2,100. Which call is doing this??
```

Most teams find out they're overspending **after** the invoice hits. StackSense gives you **full visibility** with two lines of code.

## Providers

Auto-detected. Just pass any client to `ss.monitor()`.

| Provider | Models | Pricing |
|----------|--------|---------|
| **OpenAI** | GPT-4o, GPT-4, o1, o3, embeddings | per-token |
| **Anthropic** | Claude Opus 4, Sonnet 4, 3.5 family | per-token |
| **Google** | Gemini 2.0 Flash, 1.5 Pro/Flash | per-token |
| **Mistral** | Large, Small, Nemo, Codestral | per-token |
| **Cohere** | Command R/R+, Embed v4 | per-token |
| **DeepSeek** | Chat, Reasoner | per-token |
| **AI21 Labs** | Jamba 1.5 Large/Mini, Jamba Instruct | per-token |
| **Together AI** | Llama 3.1 405B/70B/8B, Mixtral 8x22B | per-token |
| **Groq** | Llama 3.3 70B, Llama 3.1 8B, Mixtral, Gemma2 | per-token |
| **Perplexity** | Sonar Pro, Sonar, Sonar Reasoning | per-token |
| **Replicate** | Llama 3 70B/8B, SDXL, any model | per-token |
| **ElevenLabs** | All voice models | per-character |
| **Pinecone** | Vector operations | per-query |

## Features

### Multi-Provider Tracking

```python
ss = StackSense()

oai = ss.monitor(openai.OpenAI())
claude = ss.monitor(anthropic.Anthropic())

oai.chat.completions.create(model="gpt-4o", messages=[...])
claude.messages.create(model="claude-sonnet-4-20250514", messages=[...])

ss.get_cost_breakdown()
# {'openai': 0.003, 'anthropic': 0.002}
```

### Decorator

Track any function without wrapping a client:

```python
import stacksense

@stacksense.track(provider="openai", model="gpt-4o")
def generate(prompt):
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
```

Works with `async` functions too.

### Middleware

**FastAPI**
```python
from stacksense.middleware import FastAPIMiddleware
app.add_middleware(FastAPIMiddleware, stacksense=ss)
```

**Flask**
```python
from stacksense.middleware import FlaskMiddleware
FlaskMiddleware(app, stacksense=ss)
```

**Django**
```python
MIDDLEWARE = [..., 'stacksense.middleware.DjangoMiddleware']
```

### Alerts

```python
from stacksense.alerts import AlertManager, AlertRule

alerts = AlertManager(tracker=ss.tracker)
alerts.add_rule(AlertRule(
    name="Cost spike",
    metric="cost",
    threshold=5.0,
    window="1h",
))
alerts.add_webhook("https://hooks.slack.com/services/...")
alerts.check()
```

### Export

```python
from stacksense.exporters import Exporter

exporter = Exporter(ss.tracker)
exporter.to_csv("metrics.csv")
exporter.to_json("metrics.json")
```

### CLI

```bash
stacksense status              # View current metrics
stacksense dashboard           # Launch web dashboard
stacksense export csv -o out.csv
stacksense db init             # Initialize database
```

## Documentation

### Database

SQLite by default (zero config). PostgreSQL for production:

```bash
pip install stacksense[postgresql]
export STACKSENSE_DB_URL="postgresql://user:pass@host:5432/stacksense"
```

### Configuration

```bash
STACKSENSE_PROJECT_ID=my-project
STACKSENSE_ENABLE_DB=true
STACKSENSE_DB_URL=sqlite:///stacksense.db
STACKSENSE_ENVIRONMENT=production
STACKSENSE_DEBUG=false
```

## Contributing

```bash
git clone https://github.com/Abdulkvng/stacksense.git
cd stacksense
pip install -e ".[dev]"
pytest tests/ -v
```

---

## License

MIT
