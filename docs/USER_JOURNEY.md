# StackSense User Journey & Backend Flow

This document explains what happens behind the scenes when a user uses StackSense, from initialization to API call tracking to analytics.

## 🚀 Journey Overview

```
User Code → StackSense Init → Client Wrapping → API Call → Interception → 
Tracking → Database → Analytics → Results
```

---

## 📍 Step 1: Initialization

**User Code:**
```python
from stacksense import StackSense
ss = StackSense(api_key="your_key")
```

### Backend Process:

1. **Settings Creation** (`core/client.py:43-49`)
   - Creates `Settings` object from parameters or environment variables
   - Loads: `api_key`, `project_id`, `environment`, `auto_track`, `debug`
   - Defaults: SQLite database enabled, production environment

2. **Database Initialization** (`core/client.py:54-65`)
   ```
   IF enable_database == True:
       - Create DatabaseManager instance
       - Connect to database (SQLite default or PostgreSQL from URL)
       - Create tables if auto_create enabled
       - Set up connection pooling (PostgreSQL)
   ELSE:
       - Skip database setup
   ```

3. **Component Initialization** (`core/client.py:67-69`)
   - **MetricsTracker**: In-memory storage + database persistence
   - **Analytics**: Query engine for metrics analysis
   - **APIClient**: For sending data to StackSense backend API

4. **Result:**
   - StackSense instance ready with all components initialized
   - Database connection established (if enabled)
   - Logging configured

---

## 📍 Step 2: Client Wrapping

**User Code:**
```python
import openai
client = ss.monitor(openai.OpenAI())
```

### Backend Process:

1. **Provider Detection** (`core/client.py:97-110`)
   ```
   Inspect client.__module__
   - "openai" → provider = "openai"
   - "anthropic" → provider = "anthropic"
   - "elevenlabs" → provider = "elevenlabs"
   - "pinecone" → provider = "pinecone"
   - else → provider = "unknown"
   ```

2. **Client Proxy Creation** (`core/client.py:112-115`)
   - Creates `ClientProxy` wrapper around original client
   - Passes: original client, MetricsTracker, provider name
   - Proxy intercepts method calls dynamically

3. **Result:**
   - Returns wrapped client that looks/acts like original
   - All API methods are now monitored
   - User code doesn't need to change

---

## 📍 Step 3: API Call Execution

**User Code:**
```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Backend Process:

#### 3.1 Method Interception (`utils/helpers.py:28-36`)

When user calls `client.chat.completions.create()`:

1. **Attribute Access** (`ClientProxy.__getattr__`)
   ```
   User: client.chat.completions.create
   ↓
   Proxy intercepts: __getattr__("chat")
   ↓
   Returns: Chat object (also proxied)
   ↓
   Eventually reaches: create method
   ```

2. **Method Detection** (`utils/helpers.py:38-45`)
   ```
   Check if method name contains:
   - "create", "generate", "complete", "embed"
   - "query", "search", "insert", "upsert"
   - "send", "invoke"
   ↓
   IF matches → Wrap method
   ELSE → Return as-is
   ```

#### 3.2 Method Wrapping (`utils/helpers.py:47-86`)

Creates a wrapper function that:

1. **Before Call:**
   ```python
   start_time = time.time()  # Start latency timer
   model = kwargs.get("model", "unknown")  # Extract model
   ```

2. **Execute Original Call:**
   ```python
   try:
       result = method(*args, **kwargs)  # Real API call
       tokens = extract_tokens(result, provider)  # Extract usage
       return result
   except Exception as e:
       success = False
       error = str(e)
       raise  # Re-raise exception
   ```

3. **After Call (finally block):**
   ```python
   latency = (time.time() - start_time) * 1000  # Calculate ms
   
   # Track the call
   tracker.track_call(
       provider="openai",
       model="gpt-4",
       tokens={"input": 10, "output": 20},
       latency=1250.5,
       success=True,
       error=None,
       metadata={"method": "create"}
   )
   ```

#### 3.3 Token Extraction (`utils/helpers.py:88-117`)

Provider-specific extraction:

```
OpenAI:
  response.usage.prompt_tokens → input
  response.usage.completion_tokens → output

Anthropic:
  response.usage.input_tokens → input
  response.usage.output_tokens → output

ElevenLabs:
  response.character_count → characters

Pinecone:
  Always returns {"queries": 1}
```

---

## 📍 Step 4: Event Tracking

**Triggered by:** `tracker.track_call()` from Step 3.3

### Backend Process (`monitoring/tracker.py:68-138`):

#### 4.1 Event Creation (Thread-Safe)

```python
with self._lock:  # Thread lock for safety
    timestamp = datetime.utcnow().isoformat()
    
    # Calculate cost from tokens
    cost = _calculate_cost(provider, model, tokens)
    # Uses PRICING dictionary (lines 20-38)
    # Formula: (tokens / 1M) * price_per_1M
    
    # Create event dictionary
    event = {
        "timestamp": "2024-01-15T10:30:00",
        "provider": "openai",
        "model": "gpt-4",
        "tokens": {"input": 10, "output": 20},
        "total_tokens": 30,
        "cost": 0.0009,  # Calculated
        "latency": 1250.5,
        "success": True,
        "error": None,
        "metadata": {"method": "create"}
    }
```

#### 4.2 Storage (Dual Storage)

**A. In-Memory Storage:**
```python
self._events.append(event)  # Add to list
```

**B. Database Persistence** (`monitoring/tracker.py:117-118, 167-210`):
```python
IF enable_database AND db_manager exists:
    _persist_event_to_db(event, metadata)
    
    Process:
    1. Parse timestamp
    2. Create EventModel object
    3. Map event data to database columns
    4. Open database session
    5. session.add(db_event)
    6. Commit (automatic via context manager)
    7. IF error: Log warning, continue (don't fail tracking)
```

#### 4.3 Metrics Aggregation (`monitoring/tracker.py:120-132`)

Update running totals:

```python
# Global metrics
self._metrics["total_calls"] += 1
self._metrics["total_tokens"] += 30
self._metrics["total_cost"] += 0.0009

# Provider-specific metrics
provider_metrics = self._metrics["by_provider"]["openai"]
provider_metrics["calls"] += 1
provider_metrics["tokens"] += 30
provider_metrics["cost"] += 0.0009
provider_metrics["total_latency"] += 1250.5

IF not success:
    provider_metrics["errors"] += 1
```

#### 4.4 Cost Calculation (`monitoring/tracker.py:212-256`)

```python
def _calculate_cost(provider, model, tokens):
    # 1. Get provider pricing table
    provider_pricing = PRICING.get("openai", {})
    
    # 2. Find model match (fuzzy matching)
    # "gpt-4" matches "gpt-4" in PRICING
    model_pricing = {"input": 30.0, "output": 60.0}
    
    # 3. Calculate
    input_cost = (input_tokens / 1_000_000) * 30.0
    output_cost = (output_tokens / 1_000_000) * 60.0
    total_cost = input_cost + output_cost
    
    return total_cost
```

---

## 📍 Step 5: Database Persistence

**Triggered by:** Step 4.2B

### Backend Process (`monitoring/tracker.py:167-210`):

1. **Event Model Creation:**
   ```python
   db_event = EventModel(
       timestamp=datetime(2024, 1, 15, 10, 30, 0),
       project_id="default",
       environment="production",
       event_type="api_call",
       provider="openai",
       model="gpt-4",
       input_tokens=10,
       output_tokens=20,
       total_tokens=30,
       cost=0.0009,
       latency=1250.5,
       success=True,
       error=None,
       metadata={"method": "create"}
   )
   ```

2. **Database Insert:**
   ```python
   with db_manager.get_session() as session:
       session.add(db_event)
       # Auto-commit on context exit
   ```

3. **SQL Generated (PostgreSQL example):**
   ```sql
   INSERT INTO events (
       timestamp, project_id, environment,
       provider, model, input_tokens, output_tokens,
       total_tokens, cost, latency, success, metadata
   ) VALUES (
       '2024-01-15 10:30:00', 'default', 'production',
       'openai', 'gpt-4', 10, 20, 30, 0.0009, 1250.5, true, '{"method":"create"}'
   );
   ```

4. **Index Usage:**
   - Indexes on: `timestamp`, `provider`, `project_id`, `environment`
   - Fast queries for analytics

---

## 📍 Step 6: Analytics Queries

**User Code:**
```python
metrics = ss.get_metrics(timeframe="24h", from_db=True)
```

### Backend Process (`analytics/analyzer.py:26-140`):

#### 6.1 Query Decision

```python
IF from_db == True AND db_manager exists AND database enabled:
    → Query from database (_get_summary_from_db)
ELSE:
    → Query from in-memory metrics
```

#### 6.2 Database Query (`analytics/analyzer.py:74-140`)

```python
with db_manager.get_session() as session:
    # Build query
    query = session.query(EventModel).filter(
        EventModel.project_id == "default",
        EventModel.environment == "production"
    )
    
    # Apply timeframe filter
    IF timeframe == "24h":
        cutoff = datetime.utcnow() - timedelta(hours=24)
        query = query.filter(EventModel.timestamp >= cutoff)
    
    # Aggregate statistics
    stats = session.query(
        func.count(EventModel.id).label("total_calls"),
        func.sum(EventModel.total_tokens).label("total_tokens"),
        func.sum(EventModel.cost).label("total_cost"),
        func.avg(EventModel.latency).label("avg_latency"),
        func.sum(func.cast(~EventModel.success, Integer)).label("error_count")
    ).filter(...)
    
    result = stats.first()
    
    # Get unique providers
    providers = session.query(EventModel.provider).distinct().all()
```

#### 6.3 SQL Generated (Example)

```sql
SELECT 
    COUNT(id) as total_calls,
    SUM(total_tokens) as total_tokens,
    SUM(cost) as total_cost,
    AVG(latency) as avg_latency,
    SUM(CASE WHEN success = false THEN 1 ELSE 0 END) as error_count
FROM events
WHERE project_id = 'default'
  AND environment = 'production'
  AND timestamp >= '2024-01-14 10:30:00'
GROUP BY provider;
```

#### 6.4 Result Formatting

```python
return {
    "total_calls": 150,
    "total_tokens": 45000,
    "total_cost": 2.75,
    "avg_cost_per_call": 0.0183,
    "avg_latency": 1250.5,
    "error_rate": 2.0,  # 2% errors
    "providers": ["openai", "anthropic"]
}
```

---

## 📍 Step 7: Flush to Backend API

**User Code:**
```python
ss.flush()  # Or context manager exit
```

### Backend Process (`monitoring/tracker.py:309-322`):

1. **Collect Events:**
   ```python
   events = self._events.copy()  # All in-memory events
   ```

2. **Send to API** (`api/client.py:62-97`):
   ```python
   IF api_key exists:
       payload = {
           "project_id": "default",
           "environment": "production",
           "events": [event1, event2, ...]
       }
       
       POST https://api.stacksense.io/v1/events
       Headers: {
           "Authorization": "Bearer your_api_key",
           "Content-Type": "application/json"
       }
       
       IF success:
           Clear in-memory events
       ELSE:
           Log error, keep events for retry
   ```

3. **Retry Logic:**
   - Automatic retries with exponential backoff
   - Handles: 429 (rate limit), 500, 502, 503, 504
   - Max retries: 3 (configurable)

---

## 🔄 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER CODE                                │
│  ss = StackSense()                                          │
│  client = ss.monitor(openai.OpenAI())                       │
│  response = client.chat.completions.create(...)             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              STACKSENSE INITIALIZATION                      │
│  1. Create Settings (config/settings.py)                     │
│  2. Initialize Database (database/connection.py)            │
│  3. Create MetricsTracker (monitoring/tracker.py)           │
│  4. Create Analytics (analytics/analyzer.py)                │
│  5. Create APIClient (api/client.py)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              CLIENT WRAPPING                                 │
│  1. Detect Provider (openai/anthropic/etc)                  │
│  2. Create ClientProxy (utils/helpers.py)                    │
│  3. Wrap all API methods                                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              API CALL INTERCEPTION                          │
│  1. User calls: client.chat.completions.create()            │
│  2. Proxy intercepts via __getattr__                        │
│  3. Wrap method with tracking                               │
│  4. Execute original call                                    │
│  5. Extract tokens from response                            │
│  6. Calculate latency                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              EVENT TRACKING                                  │
│  1. Calculate cost (monitoring/tracker.py:212-256)          │
│  2. Create event dictionary                                  │
│  3. Store in memory (self._events)                           │
│  4. Persist to database (if enabled)                        │
│  5. Update aggregated metrics                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              DATABASE PERSISTENCE                            │
│  1. Create EventModel object (database/models.py)           │
│  2. Open database session                                    │
│  3. INSERT INTO events table                                 │
│  4. Commit transaction                                       │
│  5. Index for fast queries                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              ANALYTICS QUERY                                 │
│  1. User calls: ss.get_metrics(timeframe="24h")             │
│  2. Query from database or memory                            │
│  3. Aggregate: COUNT, SUM, AVG                              │
│  4. Filter by timeframe                                      │
│  5. Return formatted results                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              FLUSH TO BACKEND API                            │
│  1. Collect all in-memory events                            │
│  2. POST to https://api.stacksense.io/v1/events              │
│  3. Retry on failure (exponential backoff)                  │
│  4. Clear memory after success                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 Key Design Decisions

### 1. **Proxy Pattern**
- Non-intrusive: User code doesn't change
- Transparent: Wrapped client behaves identically
- Dynamic: Intercepts methods at runtime

### 2. **Dual Storage**
- **Memory**: Fast access, current session
- **Database**: Persistent, historical data
- **Backend API**: Centralized analytics

### 3. **Thread Safety**
- Locks on all shared data structures
- Safe for concurrent API calls
- Database sessions are thread-local

### 4. **Error Handling**
- Database failures don't break tracking
- API failures don't lose data
- Graceful degradation

### 5. **Performance**
- Database indexes on common queries
- Connection pooling for PostgreSQL
- Batch operations for API flush

---

## 📊 Data Flow Summary

```
API Call
  ↓
Interception (ClientProxy)
  ↓
Token Extraction
  ↓
Cost Calculation
  ↓
Event Creation
  ↓
┌─────────────┬──────────────┬─────────────┐
│   Memory    │   Database   │   API      │
│  (Fast)     │   (Persistent)  │ (Backend)  │
└─────────────┴──────────────┴─────────────┘
  ↓
Metrics Aggregation
  ↓
Analytics Queries
  ↓
User Results
```

---

## 🎯 Performance Characteristics

- **Latency Overhead**: ~1-5ms per API call (interception + tracking)
- **Database Write**: ~5-20ms (depends on database)
- **Memory Usage**: ~1KB per event (in-memory)
- **Database Size**: ~500 bytes per event (compressed)
- **Query Performance**: <100ms for 24h of data (with indexes)

---

This is the complete journey of a single API call through the StackSense system!

