# StackSense Quick Start Guide

The dashboard is **RUNNING** at: `http://127.0.0.1:5000` ✅

## 🚀 Accessing the Dashboard

1. **Open your browser**: Go to `http://127.0.0.1:5000`

2. **Click "Sign In as Test User"** (the teal button)

3. **You're in!** 🎉

## 📋 Test Account Details

- **Email**: `test@stacksense.dev`
- **Name**: Test User
- **ID**: 3 (automatically created)

## ✅ What's Already Set Up

### 1. Development Mode ✓
- No Google OAuth needed
- Test user auto-created
- Encryption key configured

### 2. Live Monitoring ✓
- Prometheus metrics at `/metrics`
- Real-time SSE stream
- System health checks running
- Alert management

### 3. Enterprise Features ✓
- Dynamic Model Routing
- Budget Enforcement
- Cost Optimization
- SLA-Aware Routing
- Governance & Audit Logs
- Agent Tracking
- Enterprise Policy Engine

## 🔑 Adding Your API Keys

Once logged in:

1. Go to **"API Keys"** tab
2. Select your provider (OpenAI, Anthropic, etc.)
3. Paste your API key
4. Click **Save**

Example API keys:
- **OpenAI**: `sk-proj-...`
- **Anthropic**: `sk-ant-...`
- **Custom**: Any provider you want

## 🧪 Testing With Real API Calls

After adding your OpenAI key:

```python
from stacksense import Client

# Initialize with test user ID
client = Client(user_id=3)

# Make a test request
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

**Check the dashboard** - you'll see:
- ✅ New event in "Recent Events"
- ✅ Updated metrics
- ✅ Cost tracking

## 📊 Exploring Live Monitoring

Click the **"Live Monitoring"** tab to see:

- **System Health** - Component status
- **Live Alerts** - Real-time notifications
- **Prometheus Metrics** - All available metrics

Connection status will show **Connected** (green) when active.

## 🛑 Stopping the Dashboard

```bash
# Press Ctrl+C in the terminal
# or kill the process
pkill -f "python.*stacksense.dashboard"
```

## 🔄 Restarting

```bash
cd /Users/kvng/projects/stacksense
./run_dev_dashboard.sh
```

## 📚 Documentation

- **Full Testing Guide**: `TESTING_GUIDE.md`
- **Enterprise Features**: `PHASE_1_PRODUCTION_FIXES.md`
- **Main README**: `README.md`

## 🎯 Next Steps

1. **Add your API keys** in the dashboard
2. **Make test API calls** using the StackSense client
3. **Monitor your usage** in real-time
4. **Set up budgets** and routing rules
5. **Explore live monitoring** features

## ⚠️ Important Notes

- This is **DEV MODE** - uses test account
- For production, set up Google OAuth (see `TESTING_GUIDE.md`)
- API keys are encrypted before storage
- Database is at `/Users/kvng/projects/stacksense/stacksense.db`

## Need Help?

- Email: abdulkvng@gmail.com
- Check `TESTING_GUIDE.md` for detailed examples
- View enterprise docs in `PHASE_1_PRODUCTION_FIXES.md`

---

**You're all set!** The dashboard is running and ready to use. 🚀
