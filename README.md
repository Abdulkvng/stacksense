<p align="center">
  <h1 align="center">⚡ StackSense</h1>
  <p align="center">
    <strong>Know exactly what your AI costs.</strong>
  </p>
  <p align="center">
    Open-source Python SDK that monitors every AI API call — tokens, cost, latency, errors.<br/>
    Drop it in. Zero config. Works across 8 providers.
  </p>
</p>

<p align="center">
  <a href="#-quickstart">Quickstart</a> •
  <a href="#-why-stacksense">Why StackSense</a> •
  <a href="#-providers">Providers</a> •
  <a href="#-features">Features</a> •
  <a href="#-docs">Docs</a>
</p>

---

## 😩 The Problem

You're shipping AI features. Costs are climbing. You have no idea which endpoint, which model, or which user is burning through your budget.

```
Month 1:  $12 in API costs. No big deal.
Month 3:  $480. Wait, what?
Month 5:  $2,100. Which call is doing this??
```

Most teams find out they're overspending **after** the invoice hits. By then it's too late.

## 💡 Why StackSense

StackSense gives you **full visibility** into your AI spend with **two lines of code**:

- 📊 **Track every call** — tokens, cost, latency, success/failure
- 💰 **Cost breakdowns** — per provider, per model, per endpoint
- ⚡ **Zero overhead** — wraps your existing client, no code changes
- 🚨 **Alerts** — get notified before costs spiral
- 📈 **Dashboard** — real-time web UI out of the box
- 🔌 **8 providers** — one SDK to monitor them all

---

## 🚀 Quickstart

```bash
pip install stacksense
```

```python
from stacksense import StackSense
import openai

ss = StackSense()
client = ss.monitor(openai.OpenAI())

# use client exactly as before — every call is now tracked
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(ss.get_metrics())
# {'total_calls': 1, 'total_tokens': 28, 'total_cost': 0.0004, ...}
```

That's it. No config files. No dashboard setup. Just `monitor()` and go.

---

## 🔌 Providers

Auto-detected. Just pass any client to `ss.monitor()`.

| Provider | Models | Pricing |
|----------|--------|---------|
| **OpenAI** | GPT-4o, GPT-4, o1, o3, embeddings | ✅ per-token |
| **Anthropic** | Claude Opus 4, Sonnet 4, 3.5 family | ✅ per-token |
| **Google** | Gemini 2.0 Flash, 1.5 Pro/Flash | ✅ per-token |
| **Mistral** | Large, Small, Nemo, Codestral | ✅ per-token |
| **Cohere** | Command R/R+, Embed v4 | ✅ per-token |
| **DeepSeek** | Chat, Reasoner | ✅ per-token |
| **ElevenLabs** | All voice models | ✅ per-character |
| **Pinecone** | Vector operations | ✅ per-query |

---

## 🧩 Features

### 🔀 Multi-Provider Tracking

```python
ss = StackSense()

oai = ss.monitor(openai.OpenAI())
claude = ss.monitor(anthropic.Anthropic())

oai.chat.completions.create(model="gpt-4o", messages=[...])
claude.messages.create(model="claude-sonnet-4-20250514", messages=[...])

ss.get_cost_breakdown()
# {'openai': 0.003, 'anthropic': 0.002}
```

### 🎯 Decorator

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

### 🛡️ Middleware

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

### 🚨 Alerts

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

### 📤 Export

```python
from stacksense.exporters import Exporter

exporter = Exporter(ss.tracker)
exporter.to_csv("metrics.csv")
exporter.to_json("metrics.json")
```

### 💻 CLI

```bash
stacksense status              # 📊 view current metrics
stacksense dashboard           # 📈 launch web dashboard
stacksense export csv -o out.csv
stacksense db init             # 💾 initialize database
```

---

## 📖 Docs

### 💾 Database

SQLite by default (zero config). PostgreSQL for production:

```bash
pip install stacksense[postgresql]
export STACKSENSE_DB_URL="postgresql://user:pass@host:5432/stacksense"
```

### ⚙️ Configuration

```bash
STACKSENSE_PROJECT_ID=my-project       # default: "default"
STACKSENSE_ENABLE_DB=true              # default: true
STACKSENSE_DB_URL=sqlite:///stacksense.db
STACKSENSE_ENVIRONMENT=production
STACKSENSE_DEBUG=false
```

---

## 🛠️ Development

```bash
git clone https://github.com/Abdulkvng/stacksense.git
cd stacksense
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 📄 License

MIT — use it however you want.
