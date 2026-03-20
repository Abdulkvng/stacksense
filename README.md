<p align="center">
  <a href="https://github.com/Abdulkvng/stacksense">
    <img src="banner.svg" alt="StackSense" width="100%">
  </a>
</p>

<p align="center">
  <strong>AI cost monitoring for Python. Two lines of code. Thirteen providers.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/stacksense/"><img src="https://img.shields.io/pypi/v/stacksense.svg?style=flat&labelColor=0a0a0a&color=6366f1" alt="PyPI"></a>
  &nbsp;
  <a href="https://github.com/Abdulkvng/stacksense/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat&labelColor=0a0a0a&color=6366f1" alt="License"></a>
  &nbsp;
  <a href="https://pypi.org/project/stacksense/"><img src="https://img.shields.io/pypi/pyversions/stacksense?style=flat&labelColor=0a0a0a&color=6366f1" alt="Python"></a>
  &nbsp;
  <img src="https://komarev.com/ghpvc/?username=Abdulkvng&repo=stacksense&label=views&color=6366f1&style=flat" alt="Views">
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a>&nbsp;&nbsp;&bull;&nbsp;&nbsp;
  <a href="#supported-providers">Providers</a>&nbsp;&nbsp;&bull;&nbsp;&nbsp;
  <a href="#features">Features</a>&nbsp;&nbsp;&bull;&nbsp;&nbsp;
  <a href="#framework-middleware">Middleware</a>&nbsp;&nbsp;&bull;&nbsp;&nbsp;
  <a href="#configuration">Config</a>&nbsp;&nbsp;&bull;&nbsp;&nbsp;
  <a href="#contributing">Contributing</a>
</p>

<br>

## The Problem

You're shipping AI features. Costs are invisible until the invoice hits.

```
Month 1    $12        "No big deal."
Month 3    $480       "Wait, what?"
Month 5    $2,100     "Which call is doing this??"
```

StackSense wraps your existing AI clients and tracks every call — tokens, latency, cost — with **zero config** and **zero code changes** to your business logic.

<br>

## Quickstart

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

That's it. No dashboards to configure. No agents to deploy. Just `monitor()` and go.

<br>

## Supported Providers

Pass any supported client to `ss.monitor()` — the provider is auto-detected.

<table>
  <tr>
    <td><strong>OpenAI</strong><br><sub>GPT-4o &bull; o1 &bull; o3 &bull; Embeddings</sub></td>
    <td><strong>Anthropic</strong><br><sub>Opus 4 &bull; Sonnet 4 &bull; Haiku</sub></td>
    <td><strong>Google</strong><br><sub>Gemini 2.0 Flash &bull; 1.5 Pro</sub></td>
    <td><strong>Mistral</strong><br><sub>Large &bull; Small &bull; Codestral</sub></td>
  </tr>
  <tr>
    <td><strong>Cohere</strong><br><sub>Command R/R+ &bull; Embed v4</sub></td>
    <td><strong>DeepSeek</strong><br><sub>Chat &bull; Reasoner</sub></td>
    <td><strong>AI21 Labs</strong><br><sub>Jamba 1.5 Large/Mini</sub></td>
    <td><strong>Together AI</strong><br><sub>Llama 3.1 &bull; Mixtral</sub></td>
  </tr>
  <tr>
    <td><strong>Groq</strong><br><sub>Llama 3.3 &bull; Mixtral &bull; Gemma2</sub></td>
    <td><strong>Perplexity</strong><br><sub>Sonar Pro &bull; Reasoning</sub></td>
    <td><strong>Replicate</strong><br><sub>Llama &bull; SDXL &bull; any model</sub></td>
    <td><strong>ElevenLabs</strong><br><sub>Voice models &bull; per-character</sub></td>
  </tr>
  <tr>
    <td><strong>Pinecone</strong><br><sub>Vector ops &bull; per-query</sub></td>
    <td colspan="3"><sub>More coming soon — <a href="https://github.com/Abdulkvng/stacksense/issues">request a provider</a></sub></td>
  </tr>
</table>

<br>

## Features

### Multi-Provider Cost Breakdown

Track spend across providers from a single `StackSense` instance.

```python
ss = StackSense()

oai = ss.monitor(openai.OpenAI())
claude = ss.monitor(anthropic.Anthropic())

oai.chat.completions.create(model="gpt-4o", messages=[...])
claude.messages.create(model="claude-sonnet-4-20250514", messages=[...])

ss.get_cost_breakdown()
# {'openai': 0.003, 'anthropic': 0.002}
```

### Decorator API

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

### Alerts & Webhooks

Get notified when costs spike.

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

<br>

## Framework Middleware

Drop-in middleware for popular frameworks — automatically tracks all AI calls per request.

<table>
<tr>
<td width="33%">

**FastAPI**

```python
from stacksense.middleware import (
    FastAPIMiddleware
)

app.add_middleware(
    FastAPIMiddleware,
    stacksense=ss
)
```

</td>
<td width="33%">

**Flask**

```python
from stacksense.middleware import (
    FlaskMiddleware
)

FlaskMiddleware(app, stacksense=ss)
```

</td>
<td width="33%">

**Django**

```python
# settings.py
MIDDLEWARE = [
    ...,
    'stacksense.middleware'
    '.DjangoMiddleware',
]
```

</td>
</tr>
</table>

<br>

## CLI

```bash
stacksense status              # View current metrics
stacksense dashboard           # Launch web dashboard
stacksense export csv -o out.csv
stacksense db init             # Initialize database
```

<br>

## Configuration

SQLite by default — zero config. PostgreSQL for production:

```bash
pip install stacksense[postgresql]
```

```bash
# Environment variables
STACKSENSE_PROJECT_ID=my-project
STACKSENSE_ENABLE_DB=true
STACKSENSE_DB_URL=postgresql://user:pass@host:5432/stacksense
STACKSENSE_ENVIRONMENT=production
STACKSENSE_DEBUG=false
```

<br>

## Contributing

```bash
git clone https://github.com/Abdulkvng/stacksense.git
cd stacksense
pip install -e ".[dev]"
pytest tests/ -v
```

PRs welcome. Please open an issue first for large changes.

<br>

<p align="center">
  <sub>MIT License &copy; 2025 StackSense Contributors</sub>
</p>
