// StackSense Dashboard JavaScript

class StackSenseDashboard {
    constructor() {
        this.currentTimeframe = '24h';
        this.costChart = null;
        this.usageChart = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadData();
        this.setupAutoRefresh();
    }

    setupEventListeners() {
        // Timeframe buttons
        document.querySelectorAll('.timeframe-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.timeframe-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentTimeframe = e.target.dataset.timeframe;
                this.loadData();
            });
        });

        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadData();
        });

        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                e.currentTarget.classList.add('active');
                // Handle view switching here
            });
        });
    }

    async loadData() {
        try {
            await Promise.all([
                this.loadMetrics(),
                this.loadCostBreakdown(),
                this.loadUsageOverTime(),
                this.loadRecentEvents()
            ]);
        } catch (error) {
            console.error('Error loading data:', error);
        }
    }

    async loadMetrics() {
        const response = await fetch(`/api/metrics/summary?timeframe=${this.currentTimeframe}`);
        const data = await response.json();

        // Update metric cards
        document.getElementById('totalCalls').textContent = this.formatNumber(data.total_calls);
        document.getElementById('totalCost').textContent = this.formatCurrency(data.total_cost);
        document.getElementById('avgLatency').textContent = `${Math.round(data.avg_latency)}ms`;
        document.getElementById('errorRate').textContent = `${data.error_rate.toFixed(2)}%`;
    }

    async loadCostBreakdown() {
        const response = await fetch(`/api/metrics/cost-breakdown?timeframe=${this.currentTimeframe}`);
        const data = await response.json();

        const providers = Object.keys(data);
        const costs = Object.values(data);
        const colors = [
            '#007AFF',
            '#5856D6',
            '#34C759',
            '#FF9500',
            '#FF3B30',
            '#AF52DE',
            '#FF2D55'
        ];

        // Update legend
        const legend = document.getElementById('costLegend');
        legend.innerHTML = providers.map((provider, i) => `
            <div class="legend-item">
                <div class="legend-color" style="background: ${colors[i % colors.length]}"></div>
                <span>${provider}</span>
            </div>
        `).join('');

        // Update chart
        const ctx = document.getElementById('costChart').getContext('2d');
        
        if (this.costChart) {
            this.costChart.destroy();
        }

        this.costChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: providers,
                datasets: [{
                    data: costs,
                    backgroundColor: colors.slice(0, providers.length),
                    borderWidth: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = this.formatCurrency(context.parsed);
                                const total = costs.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                cutout: '70%'
            }
        });
    }

    async loadUsageOverTime() {
        const response = await fetch(`/api/metrics/usage-over-time?timeframe=${this.currentTimeframe}&interval=1h`);
        const data = await response.json();

        const labels = data.map(d => {
            const date = new Date(d.timestamp);
            return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        });
        const calls = data.map(d => d.calls);
        const costs = data.map(d => d.cost);

        const ctx = document.getElementById('usageChart').getContext('2d');
        
        if (this.usageChart) {
            this.usageChart.destroy();
        }

        this.usageChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'API Calls',
                        data: calls,
                        borderColor: '#007AFF',
                        backgroundColor: 'rgba(0, 122, 255, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Cost',
                        data: costs,
                        borderColor: '#5856D6',
                        backgroundColor: 'rgba(88, 86, 214, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.datasetIndex === 0) {
                                    label += this.formatNumber(context.parsed.y);
                                } else {
                                    label += this.formatCurrency(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => this.formatNumber(value)
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        grid: {
                            drawOnChartArea: false,
                        },
                        ticks: {
                            callback: (value) => this.formatCurrency(value)
                        }
                    }
                }
            }
        });
    }

    async loadRecentEvents() {
        const response = await fetch('/api/events/recent?limit=20');
        const data = await response.json();

        const tbody = document.getElementById('eventsTableBody');
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="loading">No events found</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(event => {
            const date = new Date(event.timestamp);
            const time = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            const statusClass = event.success ? 'success' : 'error';
            const statusText = event.success ? 'Success' : 'Error';
            
            return `
                <tr>
                    <td>${time}</td>
                    <td><strong>${event.provider}</strong></td>
                    <td>${event.model || 'N/A'}</td>
                    <td>${this.formatNumber(event.total_tokens || 0)}</td>
                    <td>${this.formatCurrency(event.cost || 0)}</td>
                    <td>${Math.round(event.latency || 0)}ms</td>
                    <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                </tr>
            `;
        }).join('');
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toLocaleString();
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 4
        }).format(amount);
    }

    setupAutoRefresh() {
        // Auto-refresh every 30 seconds
        setInterval(() => {
            this.loadData();
        }, 30000);
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new StackSenseDashboard();
});

