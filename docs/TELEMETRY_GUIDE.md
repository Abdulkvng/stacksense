# StackSense Telemetry & Monitoring Guide

Complete overview of all telemetry data, metrics, and monitoring capabilities in StackSense.

## 📊 Dashboard Telemetry (Overview Tab)

### Core Metrics Cards
- **Total Calls** - Total API requests in timeframe
- **Total Cost** - Total spend across all providers
- **Average Latency** - Mean response time (ms)
- **Error Rate** - Percentage of failed requests

### Cost Breakdown (Doughnut Chart)
- Cost by provider (OpenAI, Anthropic, etc.)
- Visual percentage breakdown
- Hover for detailed amounts

### Usage Over Time (Line Chart)
- Dual-axis chart: Calls vs Cost
- Hourly/Daily buckets
- Trend visualization

### Token Usage Stats
- **Total Prompt Tokens** - All input tokens used
- **Total Completion Tokens** - All output tokens generated
- **Avg Prompt Tokens** - Average input per call
- **Avg Completion Tokens** - Average output per call

### Top Models
Shows top 5 models by cost with:
- Model name
- Total cost
- Number of calls
- Total tokens used

### Most Expensive Calls
Shows 5 most costly API calls with:
- Model used
- Provider
- Cost
- Token count
- Latency

### Recent Events Table
Real-time table showing:
- Timestamp
- Provider
- Model
- Tokens used
- Cost
- Latency
- Success/Error status

## 🏢 Enterprise Metrics (Enterprise Tab)

### Dynamic Model Routing
- **Rules Configured** - Active routing rules count
- Conditions: cost thresholds, complexity, prompt length
- Target models and fallbacks

### Budget Enforcement
- **Budgets Set** - Active budget configurations
- Scopes: global, team, feature, provider
- Actions: block, downgrade, alert
- Real-time utilization tracking

### Cost Optimization
- **Estimated Waste** - Dollar amount of inefficient calls
- **Waste %** - Percentage of total spend
- Identifies calls with 2x+ above average cost-per-token

### SLA-Aware Routing
- **SLA Configs** - Active SLA configurations
- Max latency requirements
- Success rate thresholds
- Priority levels

### Governance & Audit Logs
- **Total Events** - All audit events logged
- **Violations** - Policy violations detected
- Event categories: access, config, compliance, security

### Agent Tracking
- **Active Runs** - Currently executing agents
- **Loop Detections** - Infinite loops caught
- Workflow step tracking
- Cost per agent run

### Enterprise Policy Engine
- **Policies Set** - Active policy count
- Types: model allowlist, PII detection, data residency
- Enforcement levels: advisory, blocking

## 📡 Live Monitoring (Monitoring Tab)

### Connection Status
- **Connected/Disconnected** - Real-time SSE stream status
- Auto-reconnect on failure
- Updates every 5 seconds

### System Health
Shows health status for each component:
- Database connectivity
- API availability
- Background services
- Last check timestamp

### Live Alerts
Real-time alerts with severity levels:
- **CRITICAL** - Budget exceeded, system down, blocking violations
- **WARNING** - Budget at 90%+, loops detected, degraded performance
- **INFO** - Configuration changes, normal operations

Each alert shows:
- Timestamp
- Severity level
- Message
- Related metadata

### Prometheus Metrics Endpoint
Access raw metrics at `/metrics`:

#### Request Metrics
```
stacksense_requests_total{feature,user_id,status}
stacksense_request_duration_seconds{feature,user_id}
stacksense_request_errors_total{feature,error_type}
```

#### Budget Metrics
```
stacksense_budget_utilization_ratio{budget_id,scope,user_id}
stacksense_budget_remaining_dollars{budget_id,scope,user_id}
stacksense_budget_exceeded_total{budget_id,scope,action}
stacksense_spend_recorded_dollars_total{budget_id,scope,user_id}
```

#### Routing Metrics
```
stacksense_routing_decisions_total{rule_id,target_model,user_id}
stacksense_routing_latency_seconds{user_id}
stacksense_routing_failures_total{user_id,reason}
```

#### Agent Metrics
```
stacksense_active_agent_runs{agent_name,user_id}
stacksense_agent_cost_dollars{agent_name,status}
stacksense_agent_loop_detections_total{agent_name,user_id}
```

#### Policy Metrics
```
stacksense_policy_violations_total{policy_type,enforcement_level,user_id}
stacksense_policy_checks_total{policy_type,result}
```

#### System Metrics
```
stacksense_db_connections_active
stacksense_db_connections_idle
stacksense_system_health{component}
```

## 🔍 API Endpoints

### Overview Metrics
- `GET /api/metrics/summary?timeframe=24h` - Core metrics
- `GET /api/metrics/cost-breakdown?timeframe=24h` - Provider costs
- `GET /api/metrics/usage-over-time?timeframe=24h&interval=1h` - Time series
- `GET /api/metrics/detailed?timeframe=24h` - Detailed telemetry
- `GET /api/events/recent?limit=50` - Recent events

### Enterprise Metrics
- `GET /api/enterprise/stats` - Enterprise feature statistics

### Live Monitoring
- `GET /metrics` - Prometheus exposition format
- `GET /api/live/health` - System health status
- `GET /api/live/metrics` - Current metrics snapshot
- `GET /api/live/stream` - Server-Sent Events stream
- `GET /api/live/alerts?severity=warning&limit=100` - Get alerts
- `DELETE /api/live/alerts` - Clear all alerts

## 📈 Using Telemetry Data

### Example: Track Budget Utilization

```python
from stacksense.enterprise.monitoring import monitor

# Update budget metrics
monitor.update_budget_metrics(
    budget_id=1,
    scope="global",
    user_id="test-user",
    utilization=0.85,  # 85%
    remaining=150.0
)

# Triggers alert at 90%+
# Shows in Live Monitoring tab
# Available in Prometheus metrics
```

### Example: Track Routing Decision

```python
from stacksense.enterprise.monitoring import monitor

# Track successful routing
monitor.track_routing(
    rule_id=1,
    target_model="gpt-4o-mini",
    user_id="test-user",
    duration=0.002,
    success=True
)

# Increments stacksense_routing_decisions_total
# Updates routing_latency histogram
```

### Example: Track Agent Run

```python
from stacksense.enterprise.monitoring import monitor

# Start agent
monitor.agent_started("data-pipeline", "test-user")

# Complete agent
monitor.agent_completed(
    agent_name="data-pipeline",
    user_id="test-user",
    cost=0.52,
    status="completed",
    loop_detected=False
)

# Updates active_agent_runs gauge
# Records agent_cost distribution
```

## 🎯 Grafana Integration

Connect Grafana to StackSense Prometheus endpoint:

1. **Add Data Source**:
   - Type: Prometheus
   - URL: `http://127.0.0.1:5000/metrics`
   - Scrape interval: 15s

2. **Create Dashboard** with panels:
   - Budget utilization over time
   - Request rate by feature
   - Cost trends by provider
   - Error rates
   - Agent run durations

3. **Set Alerts**:
   - Budget utilization > 90%
   - Error rate > 5%
   - Latency p95 > 2s

## 📊 Timeframe Options

All metrics support these timeframes:
- `1h` - Last hour
- `24h` - Last 24 hours (default)
- `7d` - Last 7 days
- `30d` - Last 30 days

## 🔄 Real-Time Updates

### Auto-Refresh
- Overview tab: Refreshes every 30 seconds
- Live Monitoring: Streams updates every 5 seconds
- Manual refresh: Click "Refresh" button anytime

### Server-Sent Events
Live Monitoring uses SSE for real-time updates:
```javascript
const eventSource = new EventSource('/api/live/stream');
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // data contains: alerts, health_checks, metrics
};
```

## 💡 Best Practices

1. **Monitor Budget Utilization** - Set alerts at 80-90%
2. **Track Error Rates** - Investigate spikes immediately
3. **Analyze Cost Trends** - Identify expensive models/calls
4. **Review Agent Loops** - Prevent runaway costs
5. **Check System Health** - Ensure all components green
6. **Export to Grafana** - Long-term trend analysis
7. **Set Up Alerts** - Proactive issue detection

## 🚨 Alert Thresholds

Default alert triggers:
- Budget ≥ 90% → WARNING
- Budget exceeded → CRITICAL
- Loop detected → WARNING
- Component unhealthy → CRITICAL
- Blocking policy violation → CRITICAL

## 📝 Custom Metrics

Add custom tracking:

```python
from stacksense.enterprise.monitoring import monitor

# Track custom operation
@monitor.track_operation("my_feature")
def my_function():
    # Automatically tracks:
    # - Duration
    # - Success/error status
    # - User context
    pass
```

## 🔗 Integration Points

StackSense telemetry integrates with:
- **Prometheus** - Metrics collection
- **Grafana** - Visualization
- **AlertManager** - Alert routing
- **CloudWatch** - AWS monitoring (via Prometheus exporter)
- **Datadog** - APM integration (via StatsD)

---

**All telemetry is now available!** The dashboard shows comprehensive metrics across Overview, Enterprise, and Live Monitoring tabs. 🎉
