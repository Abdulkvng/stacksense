# StackSense Testing Guide

This guide shows you how to run and test the StackSense dashboard with real API keys.

## Quick Start (Development Mode)

### Option 1: Using the Script

```bash
# Make sure you're in the stacksense directory
cd /Users/kvng/projects/stacksense

# Run the dev dashboard
./run_dev_dashboard.sh
```

### Option 2: Manual Setup

```bash
# Set environment variables
export STACKSENSE_DEV_MODE=true
export STACKSENSE_ENCRYPTION_KEY=dev-test-key-change-this-in-production-32chars

# Run the dashboard
python -m stacksense.dashboard
```

## Accessing the Dashboard

1. **Open your browser** to `http://127.0.0.1:5000`

2. **Click "Sign In as Test User"** (the teal button)

3. **You're in!** You'll see the dashboard with the test account:
   - Email: `test@stacksense.dev`
   - Name: `Test User`

## Adding Real API Keys

Once logged in, you can test with your real API keys:

### OpenAI API Key

1. Go to the **"API Keys"** tab
2. Select **OpenAI** from the dropdown
3. Paste your API key (e.g., `sk-proj-...`)
4. Click **Save**

### Other Providers

The dashboard supports:
- **OpenAI** - `sk-...`
- **Anthropic** - `sk-ant-...`
- **ElevenLabs** - `...`
- **Pinecone** - `...`
- **Custom** - Any provider you want

### Testing API Keys Work

After adding your OpenAI key, test it with Python:

```python
from stacksense import Client

# Initialize with your user ID (test user is ID 1)
client = Client(user_id=1)

# Make a test request
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Say hello!"}]
)

print(response.choices[0].message.content)
```

Check the dashboard - you should see:
- ✅ New event in "Recent Events"
- ✅ Updated cost metrics
- ✅ Usage graphs updated

## Testing Live Monitoring

1. Go to the **"Live Monitoring"** tab
2. Watch the connection status turn **green** (Connected)
3. The system will show:
   - 🏥 **System Health** - Component status
   - 🚨 **Live Alerts** - Real-time alerts (budget warnings, etc.)
   - 📊 **Prometheus Metrics** - Available at `/metrics`

### Trigger a Test Alert

```python
from stacksense.enterprise.monitoring import monitor

# Simulate budget warning (90%+ utilization)
monitor.update_budget_metrics(
    budget_id=1,
    scope="global",
    user_id="test-user",
    utilization=0.95,  # 95% triggers warning alert
    remaining=50.0
)

# Check the Live Monitoring tab - you'll see a WARNING alert!
```

## Testing Enterprise Features

### Budget Enforcement

```python
from stacksense.enterprise.budget import BudgetEnforcer
from stacksense.enterprise.schemas import BudgetCreate
from stacksense.database import get_db_manager

db_manager = get_db_manager()

with db_manager.get_session() as session:
    enforcer = BudgetEnforcer(db_session=session, user_id=1)

    # Create a $10 daily budget
    budget = enforcer.create_budget(BudgetCreate(
        name="Daily Budget",
        scope="global",
        limit_amount=10.0,
        limit_period="daily",
        action="alert"  # or "block" or "downgrade"
    ))

    print(f"Created budget: {budget.name}")

    # Check if a request is allowed
    result = enforcer.check_budget(cost=0.50, scope="global")
    print(f"Request allowed: {result['allowed']}")
    print(f"Budget remaining: ${result['budget_remaining']:.2f}")
```

### Dynamic Routing

```python
from stacksense.enterprise.routing import DynamicRouter
from stacksense.enterprise.schemas import RoutingRuleCreate

with db_manager.get_session() as session:
    router = DynamicRouter(db_session=session, user_id=1)

    # Create routing rule: cheap model for simple tasks
    rule = router.create_rule(RoutingRuleCreate(
        name="Simple tasks → cheap model",
        conditions={
            "word_count_max": 50,  # Short prompts
            "task_complexity": "low"
        },
        target_model="gpt-4o-mini",
        fallback_model="gpt-4o",
        priority=100
    ))

    # Test routing
    result = router.route(
        prompt="What is 2+2?",
        context={"task_complexity": "low"}
    )

    print(f"Routed to: {result['model']}")  # Should be gpt-4o-mini
```

## Viewing Prometheus Metrics

Access raw metrics at: `http://127.0.0.1:5000/metrics`

You'll see metrics like:
```
# HELP stacksense_requests_total Total requests by feature
# TYPE stacksense_requests_total counter
stacksense_requests_total{feature="chat_completion",user_id="1",status="success"} 42.0

# HELP stacksense_budget_utilization_ratio Current budget utilization (0-1)
# TYPE stacksense_budget_utilization_ratio gauge
stacksense_budget_utilization_ratio{budget_id="1",scope="global",user_id="1"} 0.95
```

## Resetting the Test Environment

If you want to start fresh:

```bash
# Stop the dashboard (Ctrl+C)

# Remove the test database
rm stacksense.db

# Restart the dashboard
./run_dev_dashboard.sh
```

The test user will be recreated automatically!

## Production Setup (Google OAuth)

For production, you need Google OAuth:

1. **Create OAuth 2.0 credentials** in Google Cloud Console

2. **Add redirect URI**: `http://your-domain.com/auth/google/callback`

3. **Set environment variables**:
   ```bash
   export STACKSENSE_GOOGLE_CLIENT_ID=your_client_id
   export STACKSENSE_GOOGLE_CLIENT_SECRET=your_client_secret
   export STACKSENSE_SESSION_SECRET=random_secret_32_chars
   export STACKSENSE_ENCRYPTION_KEY=random_key_32_chars
   export STACKSENSE_DEV_MODE=false  # Disable dev mode
   ```

4. **Run the dashboard**:
   ```bash
   python -m stacksense.dashboard
   ```

## Troubleshooting

### "Module not found" errors

```bash
# Install dependencies
pip install -e .
```

### Dashboard won't start

```bash
# Check if port 5000 is in use
lsof -i :5000

# Use a different port
python -m stacksense.dashboard --port 5001
```

### API keys not working

- Make sure you saved them in the "API Keys" tab
- Check that `STACKSENSE_ENCRYPTION_KEY` is set
- Verify the key format (e.g., OpenAI keys start with `sk-`)

### No events showing up

- Make sure you're using `stacksense.Client` with the correct `user_id`
- Check that you've made at least one API call
- Refresh the dashboard (click "Refresh" button)

## Need Help?

- Check the main README: `/Users/kvng/projects/stacksense/README.md`
- View enterprise docs: `PHASE_1_PRODUCTION_FIXES.md`
- Contact: abdulkvng@gmail.com
