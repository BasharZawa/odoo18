/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

// ─────────────────────────────────────────────
//  Smart Report Builder - OWL Component
// ─────────────────────────────────────────────
class SmartReportBuilder extends Component {
    static template = "smart_report_builder.MainView";
    static props = { ...standardActionServiceProps };

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");

        this.queryInput = useRef("queryInput");
        this.chartCanvas = useRef("chartCanvas");
        this.chartInstance = null;

        this.state = useState({
            query: "",
            loading: false,
            error: null,
            data: null,
            columns: [],
            queryParams: null,
            reportTitle: "",
            chartType: "bar",
            lastModel: "",
            showSidebar: true,
            savedReports: [],
        });

        onMounted(() => {
            this.loadSavedReports();
            // Focus the input on mount
            if (this.queryInput.el) {
                this.queryInput.el.focus();
            }
            // Load Chart.js from CDN if not already loaded
            this._loadChartJS();
        });

        onWillUnmount(() => {
            if (this.chartInstance) {
                this.chartInstance.destroy();
            }
        });
    }

    // ─────────────────────────────────────────
    //  Chart.js Loader
    // ─────────────────────────────────────────
    async _loadChartJS() {
        if (window.Chart) return;
        return new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://cdn.jsdelivr.net/npm/chart.js@4.4.6/dist/chart.umd.min.js";
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    // ─────────────────────────────────────────
    //  Query Handling
    // ─────────────────────────────────────────
    onQueryInput(ev) {
        this.state.query = ev.target.value;
    }

    onQueryKeydown(ev) {
        if (ev.key === "Enter" && this.state.query.trim()) {
            this.submitQuery();
        }
    }

    useExample(text) {
        this.state.query = text;
        this.submitQuery();
    }

    async submitQuery() {
        if (!this.state.query.trim() || this.state.loading) return;

        this.state.loading = true;
        this.state.error = null;
        this.state.data = null;

        try {
            const result = await this.rpc("/smart_report/query", {
                query: this.state.query,
            });

            if (result.error) {
                this.state.error = result.error;
                return;
            }

            const params = result.query_params;
            const data = result.data;

            if (!data || data.length === 0) {
                this.state.error = "Query returned no results. Try a different question.";
                return;
            }

            // Extract columns from first row
            const columns = this._extractColumns(data, params);

            this.state.data = data;
            this.state.columns = columns;
            this.state.queryParams = params;
            this.state.reportTitle = params.title || this.state.query;
            this.state.chartType = params.chart_type || "bar";
            this.state.lastModel = params.model;

            // Render chart after DOM update
            await new Promise((r) => setTimeout(r, 100));
            this._renderChart();

        } catch (err) {
            this.state.error = `Request failed: ${err.message || err}`;
        } finally {
            this.state.loading = false;
        }
    }

    // ─────────────────────────────────────────
    //  Column Extraction
    // ─────────────────────────────────────────
    _extractColumns(data, params) {
        if (!data.length) return [];
        const firstRow = data[0];
        const columns = [];

        // Use groupby fields first, then measures
        const groupby = params.groupby || [];
        const measures = params.measures || [];
        const seen = new Set();

        // Add group-by columns
        for (const gb of groupby) {
            // Handle date groupby like "date:month"
            const key = gb.includes(":") ? gb.replace(":", ":") : gb;
            // Find the matching key in data
            const dataKey = Object.keys(firstRow).find(
                (k) => k === gb || k === key || k.startsWith(gb.split(":")[0])
            );
            if (dataKey && !seen.has(dataKey)) {
                seen.add(dataKey);
                columns.push({
                    key: dataKey,
                    label: this._humanize(dataKey),
                    type: "dimension",
                });
            }
        }

        // Add measure columns
        for (const m of measures) {
            const fieldName = m.includes(":") ? m.split(":")[0] : m;
            const dataKey = Object.keys(firstRow).find(
                (k) => k === fieldName || k === m
            );
            if (dataKey && !seen.has(dataKey)) {
                seen.add(dataKey);
                columns.push({
                    key: dataKey,
                    label: this._humanize(dataKey),
                    type: "measure",
                });
            }
        }

        // Add __count if present and not already included
        if ("__count" in firstRow && !seen.has("__count")) {
            columns.push({ key: "__count", label: "Count", type: "measure" });
        }

        // Fallback: if no columns found, use all keys
        if (columns.length === 0) {
            for (const key of Object.keys(firstRow)) {
                if (key !== "__domain") {
                    columns.push({
                        key,
                        label: this._humanize(key),
                        type: typeof firstRow[key] === "number" ? "measure" : "dimension",
                    });
                }
            }
        }

        return columns;
    }

    _humanize(str) {
        return str
            .replace(/_/g, " ")
            .replace(/([A-Z])/g, " $1")
            .replace(/:.*/, "")  // Remove :sum, :month etc
            .replace(/^\w/, (c) => c.toUpperCase())
            .trim();
    }

    // ─────────────────────────────────────────
    //  Cell Formatting
    // ─────────────────────────────────────────
    formatCell(value, col) {
        if (value === null || value === undefined || value === false) return "—";
        if (col.type === "measure" && typeof value === "number") {
            return value.toLocaleString(undefined, {
                minimumFractionDigits: 0,
                maximumFractionDigits: 2,
            });
        }
        return String(value);
    }

    // ─────────────────────────────────────────
    //  Chart Rendering
    // ─────────────────────────────────────────
    _renderChart() {
        if (this.state.chartType === "table") return;
        if (!window.Chart) return;
        if (!this.chartCanvas.el) return;

        // Destroy previous chart
        if (this.chartInstance) {
            this.chartInstance.destroy();
            this.chartInstance = null;
        }

        const data = this.state.data;
        const columns = this.state.columns;
        const dimCol = columns.find((c) => c.type === "dimension");
        const measureCols = columns.filter((c) => c.type === "measure");

        if (!dimCol || !measureCols.length) return;

        const labels = data.map((row) => {
            const v = row[dimCol.key];
            return typeof v === "string" && v.length > 25 ? v.substring(0, 25) + "…" : v;
        });

        // Color palette
        const colors = [
            "#714B67", "#017E84", "#E07C24", "#875A7B",
            "#00A09D", "#F4A460", "#3B3B98", "#38ADA9",
            "#E55039", "#4A69BD", "#6D214F", "#182C61",
        ];

        const datasets = measureCols.map((col, i) => ({
            label: col.label,
            data: data.map((row) => row[col.key] || 0),
            backgroundColor: this.state.chartType === "pie"
                ? data.map((_, j) => colors[j % colors.length])
                : colors[i % colors.length] + "CC",
            borderColor: colors[i % colors.length],
            borderWidth: 1,
            borderRadius: this.state.chartType === "bar" ? 4 : 0,
        }));

        const ctx = this.chartCanvas.el.getContext("2d");
        this.chartInstance = new window.Chart(ctx, {
            type: this.state.chartType,
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: measureCols.length > 1 || this.state.chartType === "pie",
                    },
                },
                scales: this.state.chartType === "pie" ? {} : {
                    y: { beginAtZero: true },
                    x: { ticks: { maxRotation: 45 } },
                },
            },
        });
    }

    // ─────────────────────────────────────────
    //  Chart Type Switching
    // ─────────────────────────────────────────
    setChartType(type) {
        this.state.chartType = type;
        if (type !== "table") {
            setTimeout(() => this._renderChart(), 50);
        }
    }

    // ─────────────────────────────────────────
    //  Export CSV
    // ─────────────────────────────────────────
    exportCSV() {
        if (!this.state.data || !this.state.columns.length) return;

        const cols = this.state.columns;
        const header = cols.map((c) => c.label).join(",");
        const rows = this.state.data.map((row) =>
            cols.map((c) => {
                const val = row[c.key];
                if (val === null || val === undefined) return "";
                // Escape strings with commas
                const str = String(val);
                return str.includes(",") ? `"${str}"` : str;
            }).join(",")
        );

        const csv = [header, ...rows].join("\n");
        const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${this.state.reportTitle || "report"}.csv`;
        link.click();
        URL.revokeObjectURL(url);

        this.notification.add("CSV exported successfully", { type: "success" });
    }

    // ─────────────────────────────────────────
    //  Save & Load Reports
    // ─────────────────────────────────────────
    async saveReport() {
        const name = prompt("Report name:", this.state.reportTitle);
        if (!name) return;

        try {
            const result = await this.rpc("/smart_report/save", {
                name,
                query: this.state.query,
                params: this.state.queryParams,
            });

            if (result.error) {
                this.notification.add(result.error, { type: "danger" });
            } else {
                this.notification.add("Report saved!", { type: "success" });
                this.loadSavedReports();
            }
        } catch (err) {
            this.notification.add(`Save failed: ${err}`, { type: "danger" });
        }
    }

    async loadSavedReports() {
        try {
            const reports = await this.rpc("/smart_report/saved", {});
            this.state.savedReports = reports || [];
        } catch (err) {
            // Silent fail on load
        }
    }

    async runSavedReport(reportId) {
        this.state.loading = true;
        this.state.error = null;

        try {
            const result = await this.rpc("/smart_report/run_saved", {
                report_id: reportId,
            });

            if (result.error) {
                this.state.error = result.error;
                return;
            }

            const params = result.query_params;
            const data = result.data;
            const columns = this._extractColumns(data, params);

            this.state.data = data;
            this.state.columns = columns;
            this.state.queryParams = params;
            this.state.reportTitle = params.title || "Saved Report";
            this.state.chartType = params.chart_type || "bar";
            this.state.lastModel = params.model;

            await new Promise((r) => setTimeout(r, 100));
            this._renderChart();
        } catch (err) {
            this.state.error = `Failed: ${err.message || err}`;
        } finally {
            this.state.loading = false;
        }
    }

    // ─────────────────────────────────────────
    //  UI Helpers
    // ─────────────────────────────────────────
    toggleSidebar() {
        this.state.showSidebar = !this.state.showSidebar;
    }

    clearError() {
        this.state.error = null;
    }
}

// Register as a client action
registry.category("actions").add("smart_report_builder", SmartReportBuilder);
