class StackSenseDashboard {
    constructor() {
        this.currentTimeframe = "24h";
        this.costChart = null;
        this.usageChart = null;
        this.palette = ["#0f766e", "#0d9488", "#14b8a6", "#f97316", "#ea580c", "#115e59"];
        this.liveStream = null;
        this.liveMonitoringEnabled = false;
    }

    init() {
        if (!document.body.classList.contains("app-page")) {
            return;
        }

        this.cacheElements();
        this.bindEvents();
        this.writeCallbackUrl();
        this.loadInitial();
        this.setupAutoRefresh();
    }

    cacheElements() {
        this.timeframeButtons = Array.from(document.querySelectorAll(".timeframe-btn"));
        this.sectionTabs = Array.from(document.querySelectorAll(".section-tab"));
        this.sectionPanes = Array.from(document.querySelectorAll(".section-pane"));

        this.refreshBtn = document.getElementById("refreshBtn");
        this.logoutBtn = document.getElementById("logoutBtn");

        this.userName = document.getElementById("userName");
        this.userEmail = document.getElementById("userEmail");
        this.userAvatar = document.getElementById("userAvatar");

        this.totalCalls = document.getElementById("totalCalls");
        this.totalCost = document.getElementById("totalCost");
        this.avgLatency = document.getElementById("avgLatency");
        this.errorRate = document.getElementById("errorRate");

        this.costLegend = document.getElementById("costLegend");
        this.eventsTableBody = document.getElementById("eventsTableBody");

        this.providerSelect = document.getElementById("providerSelect");
        this.customProviderRow = document.getElementById("customProviderRow");
        this.customProviderInput = document.getElementById("customProviderInput");
        this.labelInput = document.getElementById("labelInput");
        this.apiKeyInput = document.getElementById("apiKeyInput");
        this.apiKeyForm = document.getElementById("apiKeyForm");
        this.keyFormMessage = document.getElementById("keyFormMessage");

        this.apiKeysList = document.getElementById("apiKeysList");
        this.apiKeysEmpty = document.getElementById("apiKeysEmpty");
        this.refreshKeysBtn = document.getElementById("refreshKeysBtn");

        // Live monitoring elements
        this.liveHealthStatus = document.getElementById("liveHealthStatus");
        this.liveAlertsList = document.getElementById("liveAlertsList");
        this.liveAlertsEmpty = document.getElementById("liveAlertsEmpty");
        this.clearAlertsBtn = document.getElementById("clearAlertsBtn");
        this.liveStreamStatus = document.getElementById("liveStreamStatus");
    }

    bindEvents() {
        this.timeframeButtons.forEach((button) => {
            button.addEventListener("click", () => {
                this.timeframeButtons.forEach((item) => item.classList.remove("active"));
                button.classList.add("active");
                this.currentTimeframe = button.dataset.timeframe;
                this.loadData();
            });
        });

        this.sectionTabs.forEach((tab) => {
            tab.addEventListener("click", () => {
                const section = tab.dataset.section;
                this.switchSection(section);
            });
        });

        if (this.refreshBtn) {
            this.refreshBtn.addEventListener("click", async () => {
                this.refreshBtn.disabled = true;
                await this.loadData();
                await this.loadApiKeys();
                this.refreshBtn.disabled = false;
            });
        }

        if (this.logoutBtn) {
            this.logoutBtn.addEventListener("click", async () => {
                try {
                    await fetch("/logout", { method: "POST" });
                } finally {
                    window.location.href = "/login";
                }
            });
        }

        if (this.providerSelect) {
            this.providerSelect.addEventListener("change", () => {
                this.toggleCustomProvider();
            });
        }

        if (this.apiKeyForm) {
            this.apiKeyForm.addEventListener("submit", async (event) => {
                event.preventDefault();
                await this.saveApiKey();
            });
        }

        if (this.refreshKeysBtn) {
            this.refreshKeysBtn.addEventListener("click", () => {
                this.loadApiKeys();
            });
        }

        if (this.apiKeysList) {
            this.apiKeysList.addEventListener("click", async (event) => {
                const button = event.target.closest("button[data-key-id]");
                if (!button) {
                    return;
                }
                await this.deleteApiKey(Number(button.dataset.keyId));
            });
        }

        if (this.clearAlertsBtn) {
            this.clearAlertsBtn.addEventListener("click", async () => {
                await this.clearAlerts();
            });
        }
    }

    switchSection(section) {
        this.sectionTabs.forEach((tab) => {
            tab.classList.toggle("active", tab.dataset.section === section);
        });

        this.sectionPanes.forEach((pane) => {
            pane.classList.toggle("active", pane.dataset.pane === section);
        });

        if (section === "keys") {
            this.loadApiKeys();
        }
        if (section === "overview") {
            this.loadData();
        }
        if (section === "enterprise") {
            this.loadEnterpriseStats();
        }
        if (section === "monitoring") {
            this.startLiveMonitoring();
        } else {
            this.stopLiveMonitoring();
        }
    }

    toggleCustomProvider() {
        if (!this.providerSelect || !this.customProviderRow) {
            return;
        }

        const isCustom = this.providerSelect.value === "custom";
        this.customProviderRow.hidden = !isCustom;
        if (isCustom) {
            this.customProviderInput?.focus();
        }
    }

    writeCallbackUrl() {
        const callbackEl = document.getElementById("callbackUrl");
        if (callbackEl) {
            callbackEl.textContent = `${window.location.origin}/auth/google/callback`;
        }
    }

    async loadInitial() {
        await this.loadUser();
        await Promise.all([this.loadData(), this.loadApiKeys()]);
    }

    async fetchJSON(url, options = {}) {
        const headers = {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        };

        const response = await fetch(url, { ...options, headers });

        if (response.status === 401) {
            window.location.href = "/login";
            return null;
        }

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            const message = data?.error || "Request failed";
            throw new Error(message);
        }

        return data;
    }

    async loadUser() {
        try {
            const payload = await this.fetchJSON("/api/me");
            if (!payload || !payload.user) {
                return;
            }

            const { name, email, avatar_url: avatarUrl } = payload.user;
            this.userName.textContent = name || "Unknown user";
            this.userEmail.textContent = email || "";

            if (avatarUrl) {
                this.userAvatar.src = avatarUrl;
                this.userAvatar.hidden = false;
            } else {
                this.userAvatar.hidden = true;
            }
        } catch (error) {
            console.error("Failed to load user", error);
        }
    }

    async loadData() {
        this.setMetricsLoading(true);
        try {
            await Promise.all([
                this.loadMetrics(),
                this.loadCostBreakdown(),
                this.loadUsageOverTime(),
                this.loadRecentEvents(),
                this.loadDetailedMetrics(),
            ]);
        } catch (error) {
            console.error("Failed to load dashboard data", error);
        } finally {
            this.setMetricsLoading(false);
        }
    }

    async loadDetailedMetrics() {
        const data = await this.fetchJSON(`/api/metrics/detailed?timeframe=${this.currentTimeframe}`);
        if (!data) {
            return;
        }

        // Update token stats
        const tokenStats = data.token_stats || {};
        this.updateElement("totalPromptTokens", this.formatNumber(tokenStats.total_prompt_tokens || 0));
        this.updateElement("totalCompletionTokens", this.formatNumber(tokenStats.total_completion_tokens || 0));
        this.updateElement("avgPromptTokens", this.formatNumber(Math.round(tokenStats.avg_prompt_tokens || 0)));
        this.updateElement("avgCompletionTokens", this.formatNumber(Math.round(tokenStats.avg_completion_tokens || 0)));

        // Render top models
        this.renderTopModels(data.models || []);

        // Render expensive calls
        this.renderExpensiveCalls(data.expensive_calls || []);
    }

    renderTopModels(models) {
        const container = document.getElementById("topModels");
        if (!container) return;

        if (!models.length) {
            container.innerHTML = '<p class="no-data">No data available</p>';
            return;
        }

        // Sort by cost descending and take top 5
        const topModels = models.sort((a, b) => b.cost - a.cost).slice(0, 5);

        container.innerHTML = topModels.map(model => `
            <div class="list-item">
                <div class="list-item-header">
                    <span class="list-item-name">${model.model || 'Unknown'}</span>
                    <span class="list-item-value">${this.formatCurrency(model.cost)}</span>
                </div>
                <div class="list-item-meta">
                    <span>${this.formatNumber(model.calls)} calls</span>
                    <span>${this.formatNumber(model.tokens)} tokens</span>
                </div>
            </div>
        `).join("");
    }

    renderExpensiveCalls(calls) {
        const container = document.getElementById("expensiveCalls");
        if (!container) return;

        if (!calls.length) {
            container.innerHTML = '<p class="no-data">No data available</p>';
            return;
        }

        container.innerHTML = calls.map(call => `
            <div class="list-item">
                <div class="list-item-header">
                    <span class="list-item-name">${call.model || 'Unknown'}</span>
                    <span class="list-item-value">${this.formatCurrency(call.cost)}</span>
                </div>
                <div class="list-item-meta">
                    <span>${call.provider || 'Unknown'}</span>
                    <span>${this.formatNumber(call.tokens)} tokens</span>
                    <span>${Math.round(call.latency)}ms</span>
                </div>
            </div>
        `).join("");
    }

    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    setMetricsLoading(isLoading) {
        const cards = [this.totalCalls, this.totalCost, this.avgLatency, this.errorRate];
        cards.forEach((card) => {
            if (!card) {
                return;
            }
            card.style.opacity = isLoading ? "0.45" : "1";
        });
    }

    async loadMetrics() {
        const data = await this.fetchJSON(`/api/metrics/summary?timeframe=${this.currentTimeframe}`);
        if (!data) {
            return;
        }

        this.animateMetric(this.totalCalls, Number(data.total_calls || 0), (value) => this.formatNumber(value));
        this.animateMetric(this.totalCost, Number(data.total_cost || 0), (value) => this.formatCurrency(value));
        this.animateMetric(this.avgLatency, Number(data.avg_latency || 0), (value) => `${Math.round(value)}ms`);
        this.animateMetric(this.errorRate, Number(data.error_rate || 0), (value) => `${value.toFixed(1)}%`);
    }

    animateMetric(element, targetValue, formatter) {
        if (!element) {
            return;
        }

        const startValue = Number(element.dataset.value || 0);
        const duration = 500;
        const startTime = performance.now();

        const updateValue = (now) => {
            const progress = Math.min((now - startTime) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = startValue + (targetValue - startValue) * eased;

            element.textContent = formatter(current);

            if (progress < 1) {
                requestAnimationFrame(updateValue);
            } else {
                element.dataset.value = String(targetValue);
                element.textContent = formatter(targetValue);
            }
        };

        requestAnimationFrame(updateValue);
    }

    async loadCostBreakdown() {
        const data = await this.fetchJSON(`/api/metrics/cost-breakdown?timeframe=${this.currentTimeframe}`);
        if (!data) {
            return;
        }

        const providers = Object.keys(data);
        const costs = providers.map((provider) => Number(data[provider] || 0));

        this.renderCostLegend(providers);

        if (typeof Chart === "undefined") {
            return;
        }

        const ctx = document.getElementById("costChart")?.getContext("2d");
        if (!ctx) {
            return;
        }

        if (this.costChart) {
            this.costChart.destroy();
        }

        if (providers.length === 0) {
            this.costChart = new Chart(ctx, {
                type: "doughnut",
                data: {
                    labels: ["No data"],
                    datasets: [
                        {
                            data: [1],
                            backgroundColor: ["rgba(88, 112, 102, 0.22)"],
                            borderWidth: 0,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: false },
                    },
                    cutout: "72%",
                },
            });
            return;
        }

        this.costChart = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: providers,
                datasets: [
                    {
                        data: costs,
                        backgroundColor: providers.map((_, index) => this.palette[index % this.palette.length]),
                        borderWidth: 0,
                        hoverOffset: 8,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "rgba(17, 32, 26, 0.95)",
                        cornerRadius: 10,
                        callbacks: {
                            label: (context) => {
                                const total = costs.reduce((sum, value) => sum + value, 0);
                                const percent = total ? ((context.parsed / total) * 100).toFixed(1) : "0.0";
                                return `${context.label}: ${this.formatCurrency(context.parsed)} (${percent}%)`;
                            },
                        },
                    },
                },
                cutout: "72%",
            },
        });
    }

    renderCostLegend(providers) {
        if (!this.costLegend) {
            return;
        }

        if (!providers.length) {
            this.costLegend.innerHTML = "<span class=\"legend-item\">No cost data</span>";
            return;
        }

        this.costLegend.innerHTML = providers
            .map((provider, index) => {
                const color = this.palette[index % this.palette.length];
                return `
                    <span class="legend-item">
                        <span class="legend-dot" style="background:${color}"></span>
                        ${provider}
                    </span>
                `;
            })
            .join("");
    }

    async loadUsageOverTime() {
        const data = await this.fetchJSON(
            `/api/metrics/usage-over-time?timeframe=${this.currentTimeframe}&interval=1h`
        );
        if (!data || typeof Chart === "undefined") {
            return;
        }

        const hasData = data.length > 0;
        const labels = hasData
            ? data.map((point) => this.formatTimeLabel(point.timestamp))
            : ["No data"];
        const calls = hasData ? data.map((point) => point.calls) : [0];
        const costs = hasData ? data.map((point) => point.cost) : [0];

        const ctx = document.getElementById("usageChart")?.getContext("2d");
        if (!ctx) {
            return;
        }

        if (this.usageChart) {
            this.usageChart.destroy();
        }

        this.usageChart = new Chart(ctx, {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "Calls",
                        data: calls,
                        borderColor: "#0f766e",
                        backgroundColor: "rgba(15, 118, 110, 0.1)",
                        borderWidth: 2.5,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        fill: true,
                        tension: 0.38,
                        yAxisID: "y",
                    },
                    {
                        label: "Cost",
                        data: costs,
                        borderColor: "#f97316",
                        backgroundColor: "rgba(249, 115, 22, 0.1)",
                        borderWidth: 2.5,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        fill: true,
                        tension: 0.38,
                        yAxisID: "y1",
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: "index",
                },
                plugins: {
                    legend: {
                        labels: {
                            usePointStyle: true,
                            boxWidth: 8,
                            color: "#587066",
                            font: {
                                family: "Manrope",
                                size: 12,
                                weight: "600",
                            },
                        },
                    },
                    tooltip: {
                        backgroundColor: "rgba(17, 32, 26, 0.95)",
                        cornerRadius: 10,
                        callbacks: {
                            label: (context) => {
                                if (context.datasetIndex === 0) {
                                    return `Calls: ${this.formatNumber(context.parsed.y)}`;
                                }
                                return `Cost: ${this.formatCurrency(context.parsed.y)}`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: {
                            color: "#587066",
                            maxRotation: 0,
                            autoSkip: true,
                        },
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: "rgba(17, 32, 26, 0.07)",
                        },
                        ticks: {
                            color: "#587066",
                            callback: (value) => this.formatNumber(value),
                        },
                    },
                    y1: {
                        beginAtZero: true,
                        position: "right",
                        grid: { drawOnChartArea: false },
                        ticks: {
                            color: "#587066",
                            callback: (value) => this.formatCurrency(value),
                        },
                    },
                },
            },
        });
    }

    async loadRecentEvents() {
        const events = await this.fetchJSON("/api/events/recent?limit=20");
        if (!events || !this.eventsTableBody) {
            return;
        }

        if (!events.length) {
            this.eventsTableBody.innerHTML = "<tr><td colspan=\"7\" class=\"loading\">No events found.</td></tr>";
            return;
        }

        this.eventsTableBody.innerHTML = events
            .map((event) => {
                const statusClass = event.success ? "success" : "error";
                const statusText = event.success ? "Success" : "Error";
                return `
                    <tr>
                        <td>${this.formatTimeLabel(event.timestamp)}</td>
                        <td>${event.provider || "-"}</td>
                        <td>${event.model || "-"}</td>
                        <td>${this.formatNumber(event.total_tokens || 0)}</td>
                        <td>${this.formatCurrency(event.cost || 0)}</td>
                        <td>${Math.round(event.latency || 0)}ms</td>
                        <td><span class="status-pill ${statusClass}">${statusText}</span></td>
                    </tr>
                `;
            })
            .join("");
    }

    async loadApiKeys() {
        if (!this.apiKeysList) {
            return;
        }

        try {
            const keys = await this.fetchJSON("/api/user/api-keys");
            if (!keys) {
                return;
            }
            this.renderApiKeys(keys);
        } catch (error) {
            console.error("Failed to load API keys", error);
            this.renderApiKeys([]);
        }
    }

    renderApiKeys(keys) {
        if (!this.apiKeysList || !this.apiKeysEmpty) {
            return;
        }

        if (!Array.isArray(keys) || keys.length === 0) {
            this.apiKeysList.innerHTML = "";
            this.apiKeysEmpty.hidden = false;
            return;
        }

        this.apiKeysEmpty.hidden = true;
        this.apiKeysList.innerHTML = keys
            .map((item) => {
                return `
                    <li class="key-item">
                        <div class="key-meta">
                            <div>
                                <p class="key-provider">${item.provider}</p>
                                <p class="key-label">${item.label}</p>
                            </div>
                            <p class="key-hint">${item.key_hint}</p>
                        </div>
                        <p class="key-updated">Updated ${this.formatDateTime(item.updated_at)}</p>
                        <div class="key-actions">
                            <button class="delete-key-btn" type="button" data-key-id="${item.id}">Delete</button>
                        </div>
                    </li>
                `;
            })
            .join("");
    }

    async saveApiKey() {
        const provider = this.selectedProvider();
        const label = (this.labelInput?.value || "").trim();
        const apiKey = (this.apiKeyInput?.value || "").trim();

        if (!provider) {
            this.setKeyFormMessage("Please select or enter a provider.", "error");
            return;
        }

        if (!apiKey) {
            this.setKeyFormMessage("API key cannot be empty.", "error");
            return;
        }

        try {
            await this.fetchJSON("/api/user/api-keys", {
                method: "POST",
                body: JSON.stringify({
                    provider,
                    label,
                    api_key: apiKey,
                }),
            });

            this.setKeyFormMessage("API key saved.", "success");
            if (this.apiKeyInput) {
                this.apiKeyInput.value = "";
            }
            await this.loadApiKeys();
        } catch (error) {
            this.setKeyFormMessage(error.message || "Unable to save API key.", "error");
        }
    }

    selectedProvider() {
        if (!this.providerSelect) {
            return "";
        }

        if (this.providerSelect.value !== "custom") {
            return this.providerSelect.value;
        }

        const customProvider = (this.customProviderInput?.value || "").trim().toLowerCase();
        return customProvider;
    }

    async deleteApiKey(keyId) {
        if (!keyId) {
            return;
        }

        const confirmed = window.confirm("Delete this API key?");
        if (!confirmed) {
            return;
        }

        try {
            await this.fetchJSON(`/api/user/api-keys/${keyId}`, { method: "DELETE" });
            this.setKeyFormMessage("API key deleted.", "success");
            await this.loadApiKeys();
        } catch (error) {
            this.setKeyFormMessage(error.message || "Unable to delete API key.", "error");
        }
    }

    setKeyFormMessage(message, type = "") {
        if (!this.keyFormMessage) {
            return;
        }
        this.keyFormMessage.textContent = message;
        this.keyFormMessage.classList.remove("error", "success");
        if (type) {
            this.keyFormMessage.classList.add(type);
        }
    }

    setupAutoRefresh() {
        window.setInterval(() => {
            const overviewPane = document.querySelector('[data-pane="overview"]');
            if (overviewPane && overviewPane.classList.contains("active")) {
                this.loadData();
            }
        }, 30000);
    }

    // ==================== ENTERPRISE STATS ====================

    async loadEnterpriseStats() {
        try {
            const stats = await this.fetchJSON("/api/enterprise/stats");
            if (!stats) {
                return;
            }

            // Update routing rules count
            const routingElement = document.querySelector('[data-pane="enterprise"] .metric-value:nth-of-type(1)');
            if (routingElement) {
                routingElement.textContent = `${stats.routing_rules} Rules Configured`;
            }

            // Update budgets count
            const budgetsElement = document.querySelector('[data-pane="enterprise"] .metric-value:nth-of-type(2)');
            if (budgetsElement) {
                budgetsElement.textContent = `${stats.budgets} Budgets Set`;
            }

            // Update waste metrics
            const wasteElement = document.getElementById("estimatedWaste");
            if (wasteElement) {
                wasteElement.textContent = this.formatCurrency(stats.estimated_waste);
            }

            const wastePercentageElement = document.getElementById("wastePercentage");
            if (wastePercentageElement) {
                wastePercentageElement.textContent = `${stats.waste_percentage}%`;
            }

            // Update SLA configs count
            const slaElement = document.querySelector('[data-pane="enterprise"] .metric-value:nth-of-type(3)');
            if (slaElement) {
                slaElement.textContent = `${stats.sla_configs} SLA Configs`;
            }

            // Update audit events
            const auditCountElement = document.getElementById("auditEventCount");
            if (auditCountElement) {
                auditCountElement.textContent = this.formatNumber(stats.audit_events);
            }

            // Update violations (placeholder - would need actual violation tracking)
            const violationElement = document.getElementById("violationCount");
            if (violationElement) {
                violationElement.textContent = "0";
            }

            // Update agent stats
            const activeRunsElement = document.getElementById("activeAgentRuns");
            if (activeRunsElement) {
                activeRunsElement.textContent = this.formatNumber(stats.active_agent_runs);
            }

            const loopDetectionsElement = document.getElementById("loopDetections");
            if (loopDetectionsElement) {
                loopDetectionsElement.textContent = this.formatNumber(stats.loop_detections);
            }

            // Update policies count
            const policiesElement = document.querySelector('[data-pane="enterprise"] .metric-value:nth-of-type(4)');
            if (policiesElement) {
                policiesElement.textContent = `${stats.policies} Policies Set`;
            }

        } catch (error) {
            console.error("Failed to load enterprise stats", error);
        }
    }

    // ==================== LIVE MONITORING ====================

    startLiveMonitoring() {
        if (this.liveMonitoringEnabled) {
            return;
        }

        this.liveMonitoringEnabled = true;
        this.loadLiveMetrics();
        this.connectLiveStream();
    }

    stopLiveMonitoring() {
        if (!this.liveMonitoringEnabled) {
            return;
        }

        this.liveMonitoringEnabled = false;
        this.disconnectLiveStream();
    }

    connectLiveStream() {
        if (this.liveStream) {
            this.liveStream.close();
        }

        this.liveStream = new EventSource("/api/live/stream");

        this.liveStream.onopen = () => {
            this.updateStreamStatus("connected");
        };

        this.liveStream.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleLiveUpdate(data);
            } catch (error) {
                console.error("Failed to parse live metrics", error);
            }
        };

        this.liveStream.onerror = () => {
            this.updateStreamStatus("disconnected");
            setTimeout(() => {
                if (this.liveMonitoringEnabled) {
                    this.connectLiveStream();
                }
            }, 5000);
        };
    }

    disconnectLiveStream() {
        if (this.liveStream) {
            this.liveStream.close();
            this.liveStream = null;
        }
        this.updateStreamStatus("disconnected");
    }

    updateStreamStatus(status) {
        if (!this.liveStreamStatus) {
            return;
        }

        const statusMap = {
            "connected": { text: "Connected", class: "status-success" },
            "disconnected": { text: "Disconnected", class: "status-error" },
        };

        const config = statusMap[status] || statusMap["disconnected"];
        this.liveStreamStatus.textContent = config.text;
        this.liveStreamStatus.className = `stream-status ${config.class}`;
    }

    handleLiveUpdate(data) {
        if (data.error) {
            console.error("Live monitoring error:", data.error);
            return;
        }

        // Update health checks
        if (data.health_checks) {
            this.updateHealthStatus(data.health_checks);
        }

        // Update alerts
        if (data.recent_alerts) {
            this.renderLiveAlerts(data.recent_alerts);
        }
    }

    async loadLiveMetrics() {
        try {
            const data = await this.fetchJSON("/api/live/metrics");
            if (!data) {
                return;
            }

            if (data.health_checks) {
                this.updateHealthStatus(data.health_checks);
            }

            if (data.alerts) {
                this.renderLiveAlerts(data.alerts);
            }
        } catch (error) {
            console.error("Failed to load live metrics", error);
        }
    }

    updateHealthStatus(healthChecks) {
        if (!this.liveHealthStatus) {
            return;
        }

        const components = Object.keys(healthChecks);
        if (components.length === 0) {
            this.liveHealthStatus.innerHTML = "<p class=\"no-data\">No health data available</p>";
            return;
        }

        this.liveHealthStatus.innerHTML = components.map(component => {
            const status = healthChecks[component];
            const isHealthy = status.healthy;
            const statusClass = isHealthy ? "success" : "error";
            const statusText = isHealthy ? "Healthy" : "Unhealthy";
            const lastCheck = status.last_check ? this.formatDateTime(status.last_check) : "Unknown";

            return `
                <div class="health-item">
                    <div class="health-header">
                        <span class="health-component">${component}</span>
                        <span class="status-pill ${statusClass}">${statusText}</span>
                    </div>
                    <p class="health-timestamp">Last check: ${lastCheck}</p>
                </div>
            `;
        }).join("");
    }

    renderLiveAlerts(alerts) {
        if (!this.liveAlertsList || !this.liveAlertsEmpty) {
            return;
        }

        if (!Array.isArray(alerts) || alerts.length === 0) {
            this.liveAlertsList.innerHTML = "";
            this.liveAlertsEmpty.hidden = false;
            return;
        }

        this.liveAlertsEmpty.hidden = true;
        this.liveAlertsList.innerHTML = alerts.map(alert => {
            const severityClass = alert.severity === "critical" ? "error" : alert.severity === "warning" ? "warning" : "info";
            const timestamp = alert.timestamp ? this.formatDateTime(alert.timestamp) : "Unknown";

            return `
                <li class="alert-item ${severityClass}">
                    <div class="alert-header">
                        <span class="alert-severity">${alert.severity.toUpperCase()}</span>
                        <span class="alert-time">${timestamp}</span>
                    </div>
                    <p class="alert-message">${alert.message}</p>
                </li>
            `;
        }).join("");
    }

    async clearAlerts() {
        try {
            await this.fetchJSON("/api/live/alerts", { method: "DELETE" });
            this.renderLiveAlerts([]);
        } catch (error) {
            console.error("Failed to clear alerts", error);
        }
    }

    // ==================== FORMATTING ====================

    formatNumber(value) {
        return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value || 0);
    }

    formatCurrency(value) {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
            minimumFractionDigits: 2,
            maximumFractionDigits: 4,
        }).format(value || 0);
    }

    formatTimeLabel(isoString) {
        if (!isoString) {
            return "-";
        }

        const date = new Date(isoString);
        return date.toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    formatDateTime(isoString) {
        if (!isoString) {
            return "unknown";
        }

        const date = new Date(isoString);
        return date.toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const app = new StackSenseDashboard();
    app.init();
});
