# StackSense

Open-source SDK for monitoring AI API usage, cost, and performance. Drop it into any Python project — zero config, automatic tracking across 8 providers.

```bash
pip install stacksense
```

```python
from stacksense import StackSense
import openai

ss = StackSense()
client = ss.monitor(openai.OpenAI())

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(ss.get_metrics())
# {'total_calls': 1, 'total_tokens': 28, 'total_cost': 0.0004, ...}
```

That's it. Every call through `client` is now tracked — tokens, cost, latency, errors.

## Providers

Works out of the box with auto-detection:

| Provider | Models |
|----------|--------|
| **OpenAI** | GPT-4o, GPT-4, o1, o3, embeddings |
| **Anthropic** | Claude Opus 4, Sonnet 4, 3.5 family |
| **Google** | Gemini 2.0 Flash, 1.5 Pro/Flash |
| **Mistral** | Large, Small, Nemo, Codestral |
| **Cohere** | Command R/R+, Embed v4 |
| **DeepSeek** | Chat, Reasoner |
| **ElevenLabs** | All voice models (character-based) |
| **Pinecone** | Vector operations (query-based) |

## Multi-provider

```python
ss = StackSense()

oai = ss.monitor(openai.OpenAI())
claude = ss.monitor(anthropic.Anthropic())

oai.chat.completions.create(model="gpt-4o", messages=[...])
claude.messages.create(model="claude-sonnet-4-20250514", messages=[...])

ss.get_cost_breakdown()
# {'openai': 0.003, 'anthropic': 0.002}
```

## Decorator

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

Works with async functions too.

## Middleware

### FastAPI

```python
from stacksense.middleware import FastAPIMiddleware

app.add_middleware(FastAPIMiddleware, stacksense=ss)
```

### Flask

```python
from stacksense.middleware import FlaskMiddleware

FlaskMiddleware(app, stacksense=ss)
```

### Django

```python
MIDDLEWARE = [..., 'stacksense.middleware.DjangoMiddleware']
```

## Alerts

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

## Export

```python
from stacksense.exporters import Exporter

exporter = Exporter(ss.tracker)
exporter.to_csv("metrics.csv")
exporter.to_json("metrics.json")
```

## CLI

```bash
stacksense status          # view current metrics
stacksense dashboard       # launch web dashboard
stacksense export csv -o out.csv
stacksense db init         # initialize database
```

## Database

SQLite by default (zero config). PostgreSQL for production:

```bash
pip install stacksense[postgresql]
export STACKSENSE_DB_URL="postgresql://user:pass@host:5432/stacksense"
```

## Configuration

```bash
STACKSENSE_API_KEY=your_api_key       # optional
STACKSENSE_PROJECT_ID=my-project      # default: "default"
STACKSENSE_ENABLE_DB=true             # default: true
STACKSENSE_DB_URL=sqlite:///stacksense.db
STACKSENSE_ENVIRONMENT=production
STACKSENSE_DEBUG=false
```

## Development

```bash
git clone https://github.com/Abdulkvng/stacksense.git
cd stacksense
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
