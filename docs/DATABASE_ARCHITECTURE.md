# StackSense Database Architecture

## Current Implementation

### ✅ **SQLite is the DEFAULT** (Not PostgreSQL)

**Why SQLite by Default?**

1. **Zero Configuration**
   - No database server to install
   - No connection strings to configure
   - Works out of the box
   - Perfect for development and small projects

2. **File-Based**
   - Single file: `stacksense.db`
   - Easy to backup (just copy the file)
   - Portable across machines
   - No network overhead

3. **Perfect for Most Use Cases**
   - Development: Fast iteration
   - Small projects: Handles thousands of events easily
   - Testing: In-memory SQLite for tests
   - Prototyping: No infrastructure needed

**Code Location:**
```python
# stacksense/database/connection.py:40-45
if not database_url:
    db_path = os.getenv(
        "STACKSENSE_DB_PATH",
        os.path.join(os.getcwd(), "stacksense.db")
    )
    database_url = f"sqlite:///{db_path}"  # ← SQLite default
```

### ✅ **PostgreSQL is OPTIONAL** (For Production)

**When to Use PostgreSQL:**

1. **Production Environments**
   - Multiple application instances
   - High concurrency (many simultaneous writes)
   - Large datasets (millions of events)

2. **Advanced Features Needed**
   - Full-text search
   - Complex queries
   - Replication
   - High availability

3. **Team Collaboration**
   - Shared database across team
   - Centralized monitoring
   - Better access control

**How to Use PostgreSQL:**
```bash
# Install PostgreSQL support
pip install stacksense[postgres]

# Set database URL
export STACKSENSE_DB_URL="postgresql://user:pass@host:5432/stacksense"
```

---

## ✅ **YES, We Use SQLAlchemy** (And We Should!)

### Current Implementation

**We're already using SQLAlchemy 2.0+ throughout:**

1. **ORM Models** (`database/models.py`)
   ```python
   from sqlalchemy import Column, Integer, String, ...
   from sqlalchemy.ext.declarative import declarative_base
   
   class Event(Base):
       id = Column(Integer, primary_key=True)
       # ... more columns
   ```

2. **Connection Management** (`database/connection.py`)
   ```python
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker, scoped_session
   
   self.engine = create_engine(database_url, ...)
   self.SessionLocal = scoped_session(sessionmaker(...))
   ```

3. **Queries** (`analytics/analyzer.py`)
   ```python
   from sqlalchemy import func, Integer
   
   stats = session.query(
       func.count(EventModel.id),
       func.sum(EventModel.total_tokens),
       ...
   )
   ```

### Why SQLAlchemy is the Right Choice

#### ✅ **1. Database Abstraction**
- **Works with both SQLite AND PostgreSQL** (and MySQL, Oracle, etc.)
- Same code works across databases
- Easy to switch databases without code changes

#### ✅ **2. Type Safety**
- Python type hints
- IDE autocomplete
- Catch errors at development time

#### ✅ **3. ORM Benefits**
- No raw SQL strings (mostly)
- Object-oriented database access
- Automatic relationship handling
- Migrations support (via Alembic)

#### ✅ **4. Connection Pooling**
- Built-in connection pooling
- Automatic connection management
- Health checks (`pool_pre_ping`)
- Handles connection failures gracefully

#### ✅ **5. Security**
- **SQL Injection Protection**: Parameterized queries
- Input sanitization
- Type validation

#### ✅ **6. Performance**
- Query optimization
- Lazy loading
- Eager loading when needed
- Efficient batch operations

#### ✅ **7. Industry Standard**
- Most popular Python ORM
- Well-documented
- Large community
- Active development

---

## Database Comparison

| Feature | SQLite (Default) | PostgreSQL (Optional) |
|---------|------------------|----------------------|
| **Setup** | ✅ Zero config | ❌ Requires server |
| **Performance** | ✅ Fast for small/medium | ✅ Excellent for large |
| **Concurrency** | ⚠️ Limited | ✅ Excellent |
| **Scalability** | ⚠️ Single file | ✅ Unlimited |
| **Features** | ⚠️ Basic | ✅ Advanced |
| **Best For** | Dev, small projects | Production, teams |

---

## Architecture Decision: Why This Design?

### **Progressive Enhancement**

```
┌─────────────────────────────────────────┐
│  SQLite (Default)                       │
│  - Works immediately                    │
│  - No setup required                    │
│  - Perfect for 80% of users             │
└──────────────┬──────────────────────────┘
               │
               │ When you need more...
               ▼
┌─────────────────────────────────────────┐
│  PostgreSQL (Optional)                   │
│  - Set STACKSENSE_DB_URL                 │
│  - Same code, better performance         │
│  - Production-ready                      │
└─────────────────────────────────────────┘
```

### **SQLAlchemy Enables This**

Because we use SQLAlchemy:
- ✅ Same code works with both databases
- ✅ Easy migration path (just change URL)
- ✅ No code changes needed
- ✅ Database-agnostic queries

---

## Code Examples

### SQLite (Default - Automatic)
```python
from stacksense import StackSense

# SQLite is used automatically
ss = StackSense(api_key="your_key")
# Database: ./stacksense.db (created automatically)
```

### PostgreSQL (Explicit)
```python
import os
from stacksense import StackSense

# Set PostgreSQL URL
os.environ["STACKSENSE_DB_URL"] = "postgresql://user:pass@host:5432/stacksense"

ss = StackSense(api_key="your_key")
# Database: PostgreSQL (same code, different database!)
```

### Both Use Same SQLAlchemy Code
```python
# This code works with BOTH SQLite and PostgreSQL
from stacksense.database import get_db_manager, Event

db = get_db_manager()

with db.get_session() as session:
    events = session.query(Event).filter(
        Event.provider == "openai"
    ).all()
    # Works identically with both databases!
```

---

## Should We Use Raw SQL Instead?

### ❌ **No, Here's Why:**

#### **1. Database Lock-In**
```python
# Raw SQL - PostgreSQL specific
cursor.execute("SELECT * FROM events WHERE provider = %s", ("openai",))

# SQLAlchemy - Works with any database
session.query(Event).filter(Event.provider == "openai").all()
```

#### **2. SQL Injection Risk**
```python
# Raw SQL - Vulnerable
query = f"SELECT * FROM events WHERE provider = '{user_input}'"  # ❌ DANGER!

# SQLAlchemy - Safe
session.query(Event).filter(Event.provider == user_input).all()  # ✅ Safe
```

#### **3. Type Safety**
```python
# Raw SQL - No type checking
result = cursor.fetchone()
event_id = result[0]  # What type is this?

# SQLAlchemy - Type safe
event = session.query(Event).first()
event_id = event.id  # ✅ Type: int (IDE knows this)
```

#### **4. Maintenance**
```python
# Raw SQL - Hard to maintain
cursor.execute("""
    SELECT provider, COUNT(*) as calls, SUM(cost) as total_cost
    FROM events
    WHERE timestamp >= %s AND project_id = %s
    GROUP BY provider
""", (cutoff, project_id))

# SQLAlchemy - Clear and maintainable
session.query(
    Event.provider,
    func.count(Event.id).label("calls"),
    func.sum(Event.cost).label("total_cost")
).filter(
    Event.timestamp >= cutoff,
    Event.project_id == project_id
).group_by(Event.provider).all()
```

---

## Performance Considerations

### SQLite Performance
- ✅ **Fast for**: < 1M events, single user, read-heavy
- ⚠️ **Slower for**: High concurrency, many writes, large datasets

### PostgreSQL Performance
- ✅ **Fast for**: Any size, high concurrency, complex queries
- ✅ **Connection pooling**: Handles 100s of concurrent connections
- ✅ **Indexes**: Optimized for analytics queries

### SQLAlchemy Performance
- ✅ **Query optimization**: Generates efficient SQL
- ✅ **Connection pooling**: Reuses connections
- ✅ **Lazy loading**: Loads data only when needed
- ✅ **Batch operations**: Efficient bulk inserts

---

## Migration Path

### From SQLite to PostgreSQL

**Step 1:** Export data from SQLite
```bash
sqlite3 stacksense.db .dump > backup.sql
```

**Step 2:** Set PostgreSQL URL
```bash
export STACKSENSE_DB_URL="postgresql://user:pass@host:5432/stacksense"
```

**Step 3:** Restart application
```python
# Same code, different database!
ss = StackSense(api_key="your_key")
# Tables created automatically
```

**Step 4:** Import data (if needed)
```bash
psql -h host -U user -d stacksense < backup.sql
```

**No code changes needed!** Thanks to SQLAlchemy.

---

## Recommendations

### ✅ **Use SQLite When:**
- Developing locally
- Small projects (< 100K events)
- Single-user applications
- Prototyping
- Testing

### ✅ **Use PostgreSQL When:**
- Production deployments
- Multiple application instances
- High concurrency (> 10 concurrent users)
- Large datasets (> 1M events)
- Team collaboration
- Need advanced features

### ✅ **Keep Using SQLAlchemy Because:**
- It's already working perfectly
- Provides database abstraction
- Industry standard
- Well-maintained
- Secure and performant
- Makes migration easy

---

## Summary

1. **Default**: SQLite (zero config, works immediately)
2. **Optional**: PostgreSQL (for production, set URL)
3. **ORM**: SQLAlchemy (already implemented, perfect choice)
4. **Why**: Progressive enhancement, database abstraction, easy migration

**The current architecture is optimal!** ✅

