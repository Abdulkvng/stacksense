<p align="center">
  <a href="https://github.com/Abdulkvng/stacksense">
    <img src="https://raw.githubusercontent.com/Abdulkvng/stacksense/main/banner.svg" alt="StackSense" width="100%">
  </a>
</p>

<p align="center">
  <strong>Open-source AI cost monitoring for Python developers.</strong>
</p>

<p align="center">
  Track tokens, latency, cost, and provider usage across your AI stack with a simple Python SDK.
</p>

<p align="center">
  <a href="https://pypi.org/project/stacksense/"><img src="https://img.shields.io/pypi/v/stacksense.svg?style=flat&labelColor=0a0a0a&color=6366f1" alt="PyPI"></a>
  &nbsp;
  <a href="https://github.com/Abdulkvng/stacksense/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat&labelColor=0a0a0a&color=6366f1" alt="License"></a>
  &nbsp;
  <a href="https://pypi.org/project/stacksense/"><img src="https://img.shields.io/pypi/pyversions/stacksense?style=flat&labelColor=0a0a0a&color=6366f1" alt="Python"></a>
</p>

<p align="center">
  <a href="#why-stacksense">Why StackSense</a>&nbsp;&nbsp;&bull;&nbsp;&nbsp;
  <a href="#quickstart">Quickstart</a>&nbsp;&nbsp;&bull;&nbsp;&nbsp;
  <a href="#what-it-tracks">What it tracks</a>&nbsp;&nbsp;&bull;&nbsp;&nbsp;
  <a href="#supported-providers">Providers</a>&nbsp;&nbsp;&bull;&nbsp;&nbsp;
  <a href="#features">Features</a>&nbsp;&nbsp;&bull;&nbsp;&nbsp;
  <a href="#contributing">Contributing</a>
</p>

<br>

## Why StackSense

AI apps are easy to prototype but hard to monitor.

You can ship a feature using OpenAI, Anthropic, Gemini, Pinecone, ElevenLabs, or another provider in a few lines of code. But once users start using it, the important questions get harder to answer:

- How much are we spending?
- Which provider is costing the most?
- Which model is the slowest?
- Which request caused the spike?
- How many tokens are we using?
- What did this feature cost us today, this week, or this month?

StackSense gives developers a simple way to track AI usage before the invoice becomes a surprise.

```text
Month 1    $12        "No big deal."
Month 3    $480       "Wait, what?"
Month 5    $2,100     "Which call is doing this?"
```

StackSense wraps your existing AI clients and tracks every call, including tokens, latency, estimated cost, and provider usage.

No hosted dashboard required.  
No agent to deploy.  
No major rewrite.

<br>

## What StackSense does

StackSense is an open-source Python SDK that helps you monitor AI usage across providers.

It helps you:

- Track AI API calls
- Estimate model costs
- Measure latency
- Monitor token usage
- Compare provider usage
- Export metrics
- Add alerts for cost spikes
- Use middleware with FastAPI, Flask, and Django

The open-source version is focused on visibility: helping developers understand what their AI systems are doing and how much they cost.

<br>

## Quickstart

Install StackSense:

```bash
pip install stacksense
```

Use it with your existing AI client:

```python
from stacksense import StackSense
import openai

ss = StackSense()
client = ss.monitor(openai.OpenAI())

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(ss.get_metrics())
```

Example output:

```python
{
    "total_calls": 1,
    "total_tokens": 28,
    "total_cost": 0.0004,
    "average_latency": 0.82
}
```

That is it. Wrap the client once and keep using it like normal.

<br>

## What it tracks

StackSense can track:

| Metric | Description |
|---|---|
| Calls | Number of AI requests made |
| Tokens | Input, output, and total token usage |
| Cost | Estimated cost by provider and model |
| Latency | Time taken for each AI call |
| Provider | OpenAI, Anthropic, Gemini, Mistral, and more |
| Model | Model-level usage and cost breakdown |
| Errors | Failed requests and exceptions |
| Exports | CSV and JSON exports for analysis |

<br>

## Supported providers

StackSense supports multiple AI providers through one monitoring interface.

| Provider | Examples |
|---|---|
| OpenAI | GPT-4o, o1, o3, embeddings |
| Anthropic | Claude Opus, Sonnet, Haiku |
| Google | Gemini 2.0 Flash, Gemini 1.5 Pro |
| Mistral | Large, Small, Codestral |
| Cohere | Command R, Command R+, Embed |
| DeepSeek | Chat, Reasoner |
| AI21 Labs | Jamba models |
| Together AI | Llama, Mixtral |
| Groq | Llama, Mixtral, Gemma |
| Perplexity | Sonar models |
| Replicate | Hosted model calls |
| ElevenLabs | Voice and character-based usage |
| Pinecone | Vector database operations |

More providers can be added over time.

<br>

## Features

### Multi-provider tracking

Track usage across different providers in one place.

```python
ss = StackSense()

openai_client = ss.monitor(openai.OpenAI())
anthropic_client = ss.monitor(anthropic.Anthropic())

print(ss.get_cost_breakdown())
```

Example:

```python
{
    "openai": 0.003,
    "anthropic": 0.002
}
```

<br>

### Decorator API

Track custom functions with a decorator.

```python
import stacksense

@stacksense.track(provider="openai", model="gpt-4o")
def generate_response(prompt):
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
```

Async functions are supported too.

<br>

### Alerts and webhooks

Create alerts when cost or usage crosses a threshold.

```python
from stacksense.alerts import AlertManager, AlertRule

alerts = AlertManager(tracker=ss.tracker)

alerts.add_rule(AlertRule(
    name="Cost spike",
    metric="cost",
    threshold=5.0,
    window="1h"
))

alerts.check()
```

<br>

### Export metrics

Export your metrics for analysis.

```python
from stacksense.exporters import Exporter

exporter = Exporter(ss.tracker)

exporter.to_csv("metrics.csv")
exporter.to_json("metrics.json")
```

<br>

## Framework middleware

StackSense includes middleware for common Python web frameworks.

### FastAPI

```python
from stacksense.middleware import FastAPIMiddleware

app.add_middleware(
    FastAPIMiddleware,
    stacksense=ss
)
```

### Flask

```python
from stacksense.middleware import FlaskMiddleware

FlaskMiddleware(app, stacksense=ss)
```

### Django

```python
MIDDLEWARE = [
    ...
    "stacksense.middleware.DjangoMiddleware",
]
```

<br>

## CLI

StackSense also includes a CLI.

```bash
stacksense status
stacksense dashboard
stacksense export csv -o metrics.csv
stacksense db init
```

<br>

## Configuration

StackSense works with SQLite by default.

For PostgreSQL:

```bash
pip install stacksense[postgresql]
```

Example environment variables:

```bash
STACKSENSE_PROJECT_ID=my-project
STACKSENSE_ENABLE_DB=true
STACKSENSE_DB_URL=postgresql://user:pass@host:5432/stacksense
STACKSENSE_ENVIRONMENT=production
STACKSENSE_DEBUG=false
```

<br>

## OSS scope

The open-source version of StackSense focuses on monitoring and visibility.

Included in OSS:

- Python SDK
- Client monitoring
- Metrics tracking
- Cost estimation
- Provider breakdowns
- Middleware
- CLI helpers
- Export tools
- Local database support

Not included in OSS:

- AI gateway
- Runtime routing
- Budget enforcement
- Governance controls
- Enterprise policy layer

Those runtime control features are separate from the public OSS package.

<br>

## Local project structure

The repository is organized like this:

```text
stacksense/
  Core open-source Python package

tests/
  Test suite for the OSS package

examples/
  Example usage and demos
```

<br>

## Contributing

Contributions are welcome.

To run StackSense locally:

```bash
git clone https://github.com/Abdulkvng/stacksense.git
cd stacksense
pip install -e ".[dev]"
pytest tests/ -v
```

For larger changes, please open an issue first so we can discuss the direction.

<br>

## License

StackSense is released under the MIT License.

<p align="center">
  <sub>Built for developers shipping AI products with more visibility and less cost confusion.</sub>
</p>
