# StackSense Database Integration Guide

## Overview

StackSense now supports persistent storage of events and metrics in a database. This allows you to:
- Store historical data across application restarts
- Query metrics from the database for long-term analysis
- Use production-grade databases (PostgreSQL) for scalability
- Keep a local SQLite database for development

## Database Options

### SQLite (Default)
SQLite is used by default and requires no additional setup. Perfect for:
- Development and testing
- Single-user applications
- Local data storage

**Default location**: `./stacksense.db` in your current working directory

### PostgreSQL (Production)
For production use, PostgreSQL provides better performance and scalability.

**Install PostgreSQL support:**
```bash
pip install stacksense[postgres]
```

## Configuration

### Environment Variables

```bash
# Enable/disable database (default: true)
STACKSENSE_ENABLE_DB=true

# Database URL (optional - defaults to SQLite)
# SQLite: sqlite:///path/to/db.sqlite
# PostgreSQL: postgresql://user:password@host:port/dbname
STACKSENSE_DB_URL=postgresql://user:pass@localhost:5432/stacksense

# Enable SQL query logging (default: false)
STACKSENSE_DB_ECHO=false
```

### Programmatic Configuration

```python
from stacksense import StackSense

# Use default SQLite database
ss = StackSense(api_key="your_key")

# Use custom database URL
ss = StackSense(
    api_key="your_key",
    # Database will be configured via settings
)

# Or configure via Settings
from stacksense import StackSense, Settings

settings = Settings(
    enable_database=True,
    database_url="postgresql://user:pass@localhost:5432/stacksense",
    database_echo=False,  # Set to True for SQL debugging
)
ss = StackSense(api_key="your_key")
ss.settings = settings  # Update settings
```

## Database Schema

### Events Table
Stores individual API call events:
- `id`: Primary key
- `timestamp`: Event timestamp
- `project_id`: Project identifier
- `environment`: Environment (production/staging/development)
- `provider`: AI provider (openai, anthropic, etc.)
- `model`: Model name
- `input_tokens`, `output_tokens`, `total_tokens`: Token usage
- `cost`: Calculated cost
- `latency`: Response time in milliseconds
- `success`: Boolean success flag
- `error`: Error message if failed
- `metadata`: JSON metadata field
- `method`: API method name

### Metrics Table
Stores pre-aggregated metrics (for future use):
- Aggregated statistics by time period
- Provider and model breakdowns
- Pre-computed summaries

## Usage Examples

### Basic Usage (Automatic Persistence)

```python
from stacksense import StackSense
import openai

# Initialize StackSense (database enabled by default)
ss = StackSense(api_key="your_key")

# Monitor your client
client = ss.monitor(openai.OpenAI())

# All API calls are automatically tracked and persisted
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Querying from Database

```python
# Get metrics from database (instead of in-memory)
metrics = ss.get_metrics(timeframe="24h", from_db=True)

# Get events from database
events = ss.tracker.get_events(from_db=True, limit=100)
```

### Direct Database Access

```python
from stacksense.database import get_db_manager, Event

# Get database manager
db = get_db_manager()

# Query events directly
with db.get_session() as session:
    events = session.query(Event).filter(
        Event.provider == "openai"
    ).limit(10).all()
    
    for event in events:
        print(f"{event.timestamp}: {event.model} - ${event.cost}")
```

### Disable Database

```python
import os
os.environ["STACKSENSE_ENABLE_DB"] = "false"

# Or in code
from stacksense import StackSense, Settings

settings = Settings(enable_database=False)
ss = StackSense(api_key="your_key")
ss.settings = settings
```

## Database Management

### Create Tables Manually

```python
from stacksense.database import get_db_manager

db = get_db_manager()
db.create_tables()
```

### Health Check

```python
from stacksense.database import get_db_manager

db = get_db_manager()
if db.health_check():
    print("Database connection healthy")
```

### Reset Database (Development Only)

```python
from stacksense.database import get_db_manager

db = get_db_manager()
db.drop_tables()  # ⚠️ WARNING: Deletes all data
db.create_tables()
```

## Migration from In-Memory to Database

If you were using StackSense without a database, your existing code will continue to work. The database integration is backward compatible:

1. **In-memory tracking still works**: Events are stored in memory AND database
2. **Gradual migration**: You can query from database when needed
3. **No code changes required**: Existing code continues to work

## Best Practices

1. **Production**: Use PostgreSQL with connection pooling
2. **Development**: Use SQLite for simplicity
3. **Backup**: Regularly backup your database
4. **Indexing**: The schema includes indexes on common query fields
5. **Monitoring**: Monitor database size and performance

## Troubleshooting

### Database Connection Fails
- Check database URL format
- Verify database server is running (for PostgreSQL)
- Check credentials and permissions
- Review logs for detailed error messages

### Performance Issues
- Use connection pooling for PostgreSQL
- Consider batch inserts for high-volume scenarios
- Monitor database query performance
- Use indexes for common queries

### Data Not Persisting
- Verify `enable_database=True` in settings
- Check database connection health
- Review application logs for errors
- Ensure database tables are created

## Next Steps

- Set up database backups
- Configure connection pooling for production
- Implement data retention policies
- Create custom analytics queries
- Set up database monitoring


## Dashboard Authentication Tables

The dashboard now includes account and key-management persistence:

### users
Stores dashboard users created through Google OAuth:
- `id` (primary key)
- `google_sub` (unique Google user ID)
- `email` (unique)
- `name`
- `avatar_url`
- `created_at`
- `last_login_at`
- `is_active`

### user_api_keys
Stores per-user provider API keys:
- `id` (primary key)
- `user_id` (foreign key to `users.id`)
- `provider`
- `label`
- `encrypted_key`
- `key_hint` (masked display value)
- `created_at`
- `updated_at`
- `is_active`

Notes:
- Keys are encrypted before storage using `STACKSENSE_ENCRYPTION_KEY`.
- Keys are returned to the UI only as masked hints (not plaintext).
