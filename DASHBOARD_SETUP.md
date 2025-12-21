# StackSense Dashboard - Setup & Run Guide

## Quick Start

The dashboard is now ready with beautiful Apple-like aesthetics! Here's how to run it:

### 1. Install Dependencies

First, make sure Flask is installed. If you have a virtual environment, activate it first:

```bash
# Activate virtual environment (if using one)
source stacksense-venv/bin/activate  # or: source venv/bin/activate

# Install Flask (required for dashboard)
pip install flask

# Or install all dashboard dependencies
pip install "stacksense[dashboard]"
```

### 2. Run the Dashboard

You have several options to start the dashboard:

**Option A: Using the run script**
```bash
python3 run_dashboard.py
```

**Option B: Using Python directly**
```bash
python3 -c "from stacksense.dashboard.server import run_server; from stacksense.database import get_db_manager; run_server(host='127.0.0.1', port=5000, debug=True, db_manager=get_db_manager())"
```

**Option C: Using the CLI command (if set up)**
```bash
python3 -m stacksense.dashboard.cli dashboard
```

### 3. Access the Dashboard

Once the server starts, you'll see:
```
🚀 StackSense Dashboard running at http://127.0.0.1:5000
```

Open your web browser and navigate to:
**http://127.0.0.1:5000**

## Features

The dashboard includes:

- ✨ **Apple-like Design**: Clean, modern interface with glass-morphism effects
- 📊 **Real-time Metrics**: View total calls, costs, latency, and error rates
- 📈 **Interactive Charts**: Cost breakdown and usage over time visualizations
- 🔄 **Auto-refresh**: Updates every 30 seconds
- 📱 **Responsive Design**: Works on desktop and mobile devices
- ⚡ **Smooth Animations**: Beautiful transitions and micro-interactions

## Dashboard Endpoints

The dashboard provides the following API endpoints:

- `GET /` - Main dashboard page
- `GET /api/metrics/summary?timeframe=24h` - Get metrics summary
- `GET /api/metrics/cost-breakdown?timeframe=24h` - Get cost breakdown by provider
- `GET /api/metrics/usage-over-time?timeframe=24h&interval=1h` - Get usage over time
- `GET /api/events/recent?limit=50` - Get recent events

## Timeframes

You can filter data by timeframe using:
- `1h` - Last hour
- `24h` - Last 24 hours (default)
- `7d` - Last 7 days
- `30d` - Last 30 days

## Troubleshooting

**Issue: ModuleNotFoundError: No module named 'flask'**
- Solution: Install Flask with `pip install flask` or `pip install "stacksense[dashboard]"`

**Issue: Database connection errors**
- Solution: Make sure your database is set up. The dashboard uses the default SQLite database unless configured otherwise.

**Issue: No data showing**
- Solution: Make sure you have tracked some events using StackSense. The dashboard displays data from your database.

## Design Features

The dashboard features:
- Glass-morphism effects with backdrop blur
- Smooth animations and transitions
- Apple-inspired color palette
- Gradient accents
- Refined shadows and depth
- Modern typography (SF Pro Display system fonts)
- Responsive grid layouts
- Interactive hover states

Enjoy your beautiful StackSense dashboard! 🎨✨

