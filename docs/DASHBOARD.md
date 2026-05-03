# StackSense Dashboard

A beautiful, Apple-inspired web dashboard for monitoring your AI infrastructure.

## Features

- 🎨 **Sleek Design**: Apple-inspired UI with smooth animations
- 📊 **Real-time Metrics**: Live updates every 30 seconds
- 📈 **Interactive Charts**: Cost breakdown and usage over time
- 📋 **Event Log**: Recent API calls with detailed information
- ⚡ **Fast & Responsive**: Optimized for performance

## Installation

```bash
# Install with dashboard dependencies
pip install stacksense[dashboard]
```

## Quick Start

### Option 1: Python API

```python
from stacksense.dashboard import run_server

# Start dashboard server
run_server(host='127.0.0.1', port=5000, debug=True)
```

### Option 2: CLI Command

```bash
# Run dashboard
stacksense-dashboard --host 0.0.0.0 --port 5000

# With custom database
stacksense-dashboard --db-url postgresql://user:pass@host:5432/stacksense
```

### Option 3: Programmatic

```python
from stacksense import StackSense
from stacksense.dashboard import create_app

# Initialize StackSense
ss = StackSense(api_key="your_key")

# Create dashboard app
app = create_app(db_manager=ss.db_manager)

# Run with Flask
app.run(host='0.0.0.0', port=5000, debug=True)
```

## Access Dashboard

Once running, open your browser to:
```
http://localhost:5000
```

## Dashboard Features

### Overview Page
- **Metrics Cards**: Total calls, cost, latency, error rate
- **Cost Breakdown**: Doughnut chart by provider
- **Usage Over Time**: Line chart showing calls and cost trends
- **Recent Events**: Table of latest API calls

### Timeframe Selection
- **1H**: Last hour
- **24H**: Last 24 hours (default)
- **7D**: Last 7 days
- **30D**: Last 30 days

### Auto-Refresh
- Dashboard automatically refreshes every 30 seconds
- Manual refresh button available

## API Endpoints

The dashboard exposes REST API endpoints:

- `GET /api/metrics/summary?timeframe=24h` - Get metrics summary
- `GET /api/metrics/cost-breakdown?timeframe=24h` - Get cost by provider
- `GET /api/metrics/usage-over-time?timeframe=24h&interval=1h` - Get usage over time
- `GET /api/events/recent?limit=50` - Get recent events

## Customization

### Custom Port

```python
run_server(port=8080)
```

### Custom Host

```python
run_server(host='0.0.0.0', port=5000)  # Accessible from network
```

### Production Deployment

```python
from stacksense.dashboard import create_app
from waitress import serve

app = create_app()
serve(app, host='0.0.0.0', port=5000)
```

## Design Philosophy

The dashboard follows Apple's design principles:

- **Minimalism**: Clean, uncluttered interface
- **Typography**: Inter font family for readability
- **Colors**: Subtle gradients and Apple's color palette
- **Animations**: Smooth transitions and hover effects
- **Spacing**: Generous whitespace for clarity
- **Shadows**: Subtle depth with soft shadows

## Browser Support

- Chrome/Edge (latest)
- Safari (latest)
- Firefox (latest)

## Troubleshooting

### Dashboard won't start

```bash
# Check if Flask is installed
pip install flask>=3.0.0

# Check database connection
python -c "from stacksense.database import get_db_manager; get_db_manager().health_check()"
```

### No data showing

- Ensure StackSense is tracking events
- Check database has events: `SELECT COUNT(*) FROM events;`
- Verify database connection in dashboard logs

### Charts not rendering

- Check browser console for JavaScript errors
- Ensure Chart.js is loading (check Network tab)
- Try hard refresh (Cmd+Shift+R / Ctrl+Shift+R)

## Development

### Run in Development Mode

```python
run_server(debug=True)
```

### Customize Styling

Edit `stacksense/dashboard/static/css/style.css`

### Customize JavaScript

Edit `stacksense/dashboard/static/js/dashboard.js`

## Screenshots

The dashboard features:
- Sidebar navigation
- Metric cards with gradients
- Interactive charts
- Event table with status badges
- Responsive design

## Next Steps

- Add more chart types
- Export data functionality
- Alert configuration
- User authentication
- Multi-project support

