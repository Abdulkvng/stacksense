# 🏗️ StackSense - The Ultimate Internal Architecture Guide

*Note: This file is intentionally added to `.gitignore`. It is your personal, behind-the-scenes reference map to the exact architecture and flow of the StackSense application.*

---

## 🧭 The High-Level Map: How Data Flows
When a developer initiates a request through StackSense, here is how the modules interact:
1. **Core (`core/client.py`)**: The user creates a `StackSense()` instance. This is the "brain" and entrypoint.
2. **Proxy/API (`api/client.py`)**: The request is routed to the actual LLM (OpenAI, Claude). 
3. **Monitoring (`monitoring/tracker.py`)**: In parallel, metrics about the prompt, tokens, and latency are intercepted.
4. **Database (`database/models.py`)**: The intercepted data is saved (SQLite by default, or Postgres).
5. **Analytics (`analytics/analyzer.py`)**: Crunching raw DB rows into "insights" (like total weekly spend).
6. **Dashboard (`dashboard/server.py`)**: A Flask web server that visualizes the Analytics data on local charts.

---

## 📁 Detailed Directory Breakdown

### 1. `/stacksense/` (The Main Application Package)

* **`__init__.py`**: 
  * **Why it's here:** Makes this directory a standard Python package. It imports critical classes (`StackSense`, `MetricsTracker`, `Settings`) so users can type `from stacksense import StackSense` cleanly instead of memorizing nested paths.

* **`core/`** (The Entrypoint)
  * **`client.py`**: Contains the main `StackSense` class. **Why:** It acts as the facade/orchestrator. When a user calls `stacksense.track()`, this file delegates the work to the Tracker, Logger, and API.

* **`api/`** (External Communication)
  * **`client.py`**: **Why:** Abstracts away the differences between hitting OpenAI's API vs Anthropic's API vs ElevenLabs. It standardizes HTTP calls.

* **`monitoring/`** (The Watchdogs)
  * **`tracker.py`**: The `MetricsTracker` class lives here. **Why:** It intercepts network calls to measure how long an LLM took to reply, and intercepts the payload to count token usage.

* **`analytics/`** (The Number Crunchers)
  * **`analyzer.py`**: Contains the `Analytics` class. **Why:** Once raw data is in the database, this aggregates it into structured data formats (JSON/pandas) that the frontend dashboard can actually understand.

* **`database/`** (Storage Layer)
  * **`models.py`**: Defines the SQLAlchemy mapping (e.g., the `RequestLog` and `TokenUsage` tables). **Why:** Maps Python objects to database rows seamlessly.
  * **`connection.py`**: **Why:** Handles initializing SQLite/Postgres engines, establishing connection pools, and providing database sessions to the rest of the app securely.

* **`config/`** (Settings)
  * **`settings.py`**: Defines environment variables (`STACKSENSE_DB_URL`, etc). **Why:** Prevents hardcoding secrets in the logic.

* **`logger/`** (System Feedback)
  * **`logger.py`**: Standardized console printing. **Why:** Ensures info/warning/error logs have a consistent format.

* **`utils/`** (Helper Functions)
  * **`helpers.py`**: A catch-all for small, pure logic functions. **Why:** Functions like `calculate_cost_for_tokens(model_name)` or `format_latency()` shouldn't clutter the core logic.

* **`dashboard/`** (The User Interface)
  * **`server.py`**: The Flask application backend. **Why:** Starts the web server and defines the API endpoints the UI needs.
  * **`security.py`**: Auth/login checks for the dashboard interface.
  * **`cli.py`**: Console commands (if you run `stacksense-ui` from a terminal).
  * **`templates/` & `static/`**: Standard web assets. **`index.html`** is the main view, while **`style.css`** shapes the visual identity.

---

### 2. Root-Level Files

* **`run_dashboard.py`**
  * **Why it's here:** This is a high-level boot script. It simply imports the Flask server from `stacksense/dashboard/` and runs it on port 5000. It is a quick-start alias.
* **`get_log.py` / `fetch_logs.py`**
  * **Why they are here:** These are your internal scratchpads/scripts used for testing connection logic or viewing raw logs without booting the full dashboard. 
* **`pyproject.toml`**
  * **Why it's here:** The standard recipe defining how this package is built, its dependencies (like SQLAlchemy, requests), and how it should be installed via `pip`.
* **`tests/`**
  * **Why it's here:** Your massive suite of `pytest` unit tests (138 files!). It lives outside `stacksense/` so testing logic isn't packaged alongside production code.
* **`.github/workflows/ci.yml`**
  * **Why it's here:** Tells GitHub Actions to automatically run `pytest tests/` every time you push code, ensuring you don't break things accidentally.

---
*If you ever want to resume the Open-Core monolith design for Enterprise pricing in the future, we will split the directories back out, but maintain this exact same underlying data flow!*
