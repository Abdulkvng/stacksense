# 🏗️ StackSense Architecture

How StackSense works under the hood. If you're contributing or just curious, this is for you.

---

## 📁 Project Structure

```
stacksense/
├── __init__.py              # Package entry — exports StackSense, track, etc.
├── core/
│   └── client.py            # 🎯 Main StackSense class — the entry point for everything
├── monitoring/
│   └── tracker.py           # 📊 Metrics engine — tracks tokens, cost, latency per call
├── utils/
│   └── helpers.py           # 🔀 Proxy wrappers — intercepts API calls transparently
├── config/
│   └── settings.py          # ⚙️ Configuration — loads from env vars
├── analytics/
│   └── analyzer.py          # 📈 Analytics — aggregates metrics, time-series, breakdowns
├── database/
│   ├── connection.py        # 💾 DB connection manager (SQLite/PostgreSQL)
│   └── models.py            # 📋 SQLAlchemy models (Event, Metric, etc.)
├── decorators.py            # 🎯 @track() decorator for function-level monitoring
├── middleware.py            # 🛡️ FastAPI / Flask / Django middleware
├── alerts.py                # 🚨 Alert rules + webhook notifications
├── exporters.py             # 📤 CSV / JSON export
├── cli.py                   # 💻 CLI commands (dashboard, status, export, db)
├── logger/
│   └── logger.py            # 📝 Structured logging
├── api/
│   └── client.py            # 🌐 HTTP client for StackSense backend API
└── dashboard/
    └── server.py            # 📈 Flask web dashboard with Google OAuth
```

---

## 🔄 How Monitoring Works

The core idea: **wrap the user's AI client in a proxy that intercepts every API call, extracts metrics, and tracks them — without changing any user code.**

### The Flow

```
Your code                         StackSense (behind the scenes)
─────────                         ─────────────────────────────

ss = StackSense()                 → Initializes Settings, DB, Tracker, Analytics
client = ss.monitor(openai)       → Detects provider, wraps client in ClientProxy
                                    (returns a proxy that looks identical to the original)

client.chat.completions.create()  → Proxy chains: chat → completions → create
                                  → Detects "create" is an API method
                                  → Wraps the call:
                                      1. Start timer
                                      2. Call the real method
                                      3. Extract tokens from response
                                      4. Calculate cost from pricing table
                                      5. tracker.track_call() → save to DB
                                  → Returns the original response unchanged
```

---

## 🧩 Key Files Explained

### `core/client.py` — The Hub

This is what users interact with. The `StackSense` class ties everything together.

**What it does:**
- `monitor(client)` — Auto-detects the provider (OpenAI, Anthropic, etc.) by checking the client's module name, then wraps it in a proxy
- `get_metrics()` / `get_cost_breakdown()` — Delegates to Analytics
- `track_event()` — Manual event tracking
- `flush()` — Sends queued events to the StackSense API

**Provider detection** works by inspecting `client.__class__.__module__`:
```python
"openai."     → "openai"
"anthropic."  → "anthropic"
"google."     → "google"
"mistral."    → "mistral"
# ... etc
```

---

### `utils/helpers.py` — The Proxy Engine

This is where the magic happens. Two classes: `ClientProxy` (sync) and `AsyncClientProxy` (async).

**How the proxy works:**

Every attribute access goes through `__getattr__`. When you write `client.chat.completions.create(...)`:

1. `.chat` → not an API method → returns a new proxy wrapping `client.chat`
2. `.completions` → not an API method → returns a new proxy wrapping `client.chat.completions`
3. `.create` → IS an API method → returns a wrapped function that tracks the call

**API method detection** — checks if the method name matches known patterns:
`create`, `generate`, `embed`, `query`, `complete`, `transcribe`, `translate`, etc.

**Token extraction** — each provider returns usage differently:
```python
# OpenAI:      response.usage.prompt_tokens / completion_tokens
# Anthropic:   response.usage.input_tokens / output_tokens
# Google:      response.usage_metadata.prompt_token_count / candidates_token_count
# Mistral:     response.usage.prompt_tokens / completion_tokens
# Cohere:      response.meta.tokens.input_tokens / output_tokens
# DeepSeek:    response.usage.prompt_tokens / completion_tokens
```

**Streaming** — if the response is a generator/stream, the proxy collects chunks and tracks the full call after the stream ends.

---

### `monitoring/tracker.py` — The Metrics Engine

Receives tracked calls and does three things:

1. **Calculates cost** using a built-in pricing table (per-model, per-provider, input vs output rates)
2. **Aggregates in memory** — running totals for total_calls, total_tokens, total_cost, by_provider
3. **Persists to database** — creates an `Event` row for each API call

The pricing table covers all supported models:
```python
PRICING = {
    "openai": {
        "gpt-4o":      {"input": 2.50, "output": 10.00},   # per 1M tokens
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "o1":          {"input": 15.00, "output": 60.00},
        ...
    },
    "anthropic": {
        "claude-opus-4": {"input": 15.00, "output": 75.00},
        ...
    },
    # ... 8 providers total
}
```

---

### `analytics/analyzer.py` — Query Layer

Takes raw events and produces insights:

- `get_summary(timeframe)` — total calls, tokens, cost, avg latency, error rate
- `get_cost_breakdown()` — cost per provider
- `get_performance_stats()` — latency, error rate, tokens per provider
- `get_usage_over_time(interval)` — time-series data bucketed by hour/day
- `get_top_models()` — most-used models by call count

Can query from in-memory events or directly from the database with SQL aggregations for performance.

---

### `database/connection.py` + `models.py` — Persistence

**connection.py** — SQLAlchemy engine setup with a singleton `DatabaseManager`. Defaults to SQLite (zero config), supports PostgreSQL.

**models.py** — The `Event` model stores everything about each API call:
```
id | timestamp | provider | model | input_tokens | output_tokens
total_tokens | cost | latency | success | error | project_id | environment
```

Indexed on `(provider, timestamp)`, `(project_id, environment, timestamp)`, and `(model, timestamp)` for fast dashboard queries.

---

### `config/settings.py` — Configuration

Dataclass that loads from environment variables:

| Env Var | What it controls |
|---------|-----------------|
| `STACKSENSE_PROJECT_ID` | Groups events by project |
| `STACKSENSE_ENABLE_DB` | Toggle database persistence |
| `STACKSENSE_DB_URL` | SQLite or PostgreSQL connection |
| `STACKSENSE_ENVIRONMENT` | Tag events (production, staging, etc.) |
| `STACKSENSE_DEBUG` | Verbose logging |

---

### `decorators.py` — Alternative API

`@track()` is for when you don't want to wrap a client — just decorate a function:

```python
@stacksense.track(provider="openai", model="gpt-4o")
def my_function(prompt):
    ...
```

It wraps the function, times execution, tries to extract tokens from the return value, and calls `tracker.track_call()`. Works with sync and async functions.

---

### `middleware.py` — Framework Integration

Middleware for FastAPI (ASGI), Flask, and Django. Tracks HTTP request latency and errors at the framework level as custom events — separate from AI API call tracking.

---

### `alerts.py` — Notifications

Define rules like "alert me if hourly cost > $5":

```python
AlertRule(name="Cost spike", metric="cost", threshold=5.0, window="1h")
```

`AlertManager.check()` evaluates rules against current metrics and fires webhooks or Python callbacks. Supports cooldowns to avoid spam.

---

### `exporters.py` — Data Export

Pulls events from the tracker and writes to CSV or JSON. Can include an analytics summary. Used by the CLI (`stacksense export csv -o file.csv`).

---

### `dashboard/server.py` — Web UI

Flask app with:
- Google OAuth login
- REST API endpoints (`/api/metrics/summary`, `/api/events/recent`, etc.)
- Server-Sent Events for real-time streaming
- Encrypted API key storage per user

The dashboard frontend (JS) polls these endpoints to render charts and tables.

---

### `api/client.py` — Backend Communication

HTTP client with retry logic (exponential backoff). Used by `tracker.flush()` to send batched events to a remote StackSense API if configured.

---

## 🗺️ Data Flow Diagram

```
┌──────────────┐
│   Your Code  │  client.chat.completions.create(...)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ ClientProxy  │  Intercepts call, times it, extracts tokens
│ (helpers.py) │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Tracker    │  Calculates cost, aggregates metrics
│ (tracker.py) │
└──────┬───────┘
       │
       ├────────────────┐
       ▼                ▼
┌──────────────┐  ┌──────────────┐
│   Database   │  │  In-Memory   │
│  (SQLite/PG) │  │   Metrics    │
└──────┬───────┘  └──────┬───────┘
       │                 │
       ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Dashboard   │  │  Analytics   │  │   Alerts     │
│  (Flask UI)  │  │  (analyzer)  │  │  (webhooks)  │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 🤝 Contributing

Understanding the architecture? Here's where to start:

- **Add a new provider** → Update `_detect_provider()` in `core/client.py`, add token extraction in `helpers.py`, add pricing in `tracker.py`
- **Add a new metric** → Update `track_call()` in `tracker.py`, add aggregation in `analyzer.py`
- **Add a dashboard endpoint** → Add route in `dashboard/server.py`
- **Add an export format** → Add method to `Exporter` in `exporters.py`
