let chart;
let ignoreLiveUntil = 0;
let currentWeatherData = {};
let currentInterval = 60; // Track the current active interval
let lastLoadTime = 0;
let pendingLoad = null;

// Get current page URL to determine if dashboard or forecasting
function isForcastingPage() {
    return window.location.pathname.includes('forecasting');
}

function parseDashboardLabelToForecastParams(label) {
    // Label can be "HH:MM" or "YYYY-MM-DD HH:MM"
    if (!label) return null;

    let datePart = '';
    let timePart = '';
    if (label.includes(' ')) {
        const parts = label.split(' ');
        datePart = parts[0];
        timePart = parts[1];
    } else {
        datePart = new Date().toISOString().slice(0, 10);
        timePart = label;
    }

    const [hhStr, mmStr] = timePart.split(':');
    const hh24 = parseInt(hhStr, 10);
    const mm = parseInt(mmStr, 10);

    const ampm = hh24 >= 12 ? "PM" : "AM";
    const hour12 = ((hh24 + 11) % 12) + 1; // 0-23 -> 1-12

    const time12 = String(hour12).padStart(2, '0') + ":" + String(mm).padStart(2, '0');

    return { date: datePart, time: time12, am_pm: ampm };
}

function applyForecastToGauges(data) {
    setValue("temperature", data.temperature, tempGauge);
    setValue("humidity", data.humidity, humidityGauge);
    setValue("wind_speed", data.wind_speed, windGauge);
    setValue("rainfall", data.rainfall, rainGauge);
    setValue("solar_radiation", data.solar_radiation, solarGauge);

    const dirEl = document.getElementById("wind_direction");
    if (dirEl) dirEl.innerText = data.wind_direction + "°";
}

function getForecastForDashboardLabel(label, horizon = 1) {
    const params = parseDashboardLabelToForecastParams(label);
    if (!params) return;

    // Keep prediction visible even though live updates continue.
    ignoreLiveUntil = Date.now() + 10000;

    fetch(`/api/forecast?date=${params.date}&time=${params.time}&am_pm=${params.am_pm}&horizon=${horizon}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) return;
            applyForecastToGauges(data);
        })
        .catch(err => console.error(err));
}

function loadDashboard(interval) {
    // Debouncing: prevent rapid successive calls within 100ms
    const now = Date.now();
    if (now - lastLoadTime < 100) {
        clearTimeout(pendingLoad);
        pendingLoad = setTimeout(() => {
            loadDashboard(interval);
        }, 100 - (now - lastLoadTime));
        return;
    }
    lastLoadTime = now;
    
    // Save current interval
    currentInterval = interval;
    
    const fromDate = document.getElementById('fromDate').value;
    const toDate = document.getElementById('toDate').value;

    // Clear all active states first
    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Update active button state IMMEDIATELY (no delays)
    const activeBtn = document.querySelector(`.time-btn[data-interval="${interval}"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }

    // Determine URL based on Date Range or Interval
    let url = `/api/dashboard?interval=${interval}`;
    if (fromDate && toDate) {
        url = `/api/dashboard?start_date=${fromDate}&end_date=${toDate}&interval=${interval}`;
    }

    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (chart) chart.destroy();

            Chart.defaults.color = document.body.classList.contains('dark') ? '#9CA3AF' : '#6B7280';
            Chart.defaults.borderColor = document.body.classList.contains('dark') ? '#374151' : '#E5E7EB';

            const ctx = document.getElementById("weatherChart").getContext('2d');

            // Check Active Params - only allow Temperature (0), Humidity (1), Solar (4) to be visible
            // Disabled parameters (Rain=2, Wind=3, Direction=5) should always be hidden
            const disabledIndices = [2, 3, 5]; // Rainfall, Wind Speed, Wind Direction
            const paramFlags = [
                true,  // Temp - always true (active)
                true,  // Humid - always true (active)
                false, // Rain - always false (disabled)
                false, // Wind - always false (disabled)
                true,  // Solar - always true (active)
                false  // Direction - always false (disabled)
            ];

            const gradTemp = ctx.createLinearGradient(0, 0, 0, 400);
            gradTemp.addColorStop(0, 'rgba(244, 114, 182, 0.5)');
            gradTemp.addColorStop(1, 'rgba(244, 114, 182, 0)');

            const gradHum = ctx.createLinearGradient(0, 0, 0, 400);
            gradHum.addColorStop(0, 'rgba(45, 212, 191, 0.5)');
            gradHum.addColorStop(1, 'rgba(45, 212, 191, 0)');

            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.timestamps,
                    datasets: [
                        { ...createSet("Temperature", data.data.temperature, "#F472B6", gradTemp), hidden: !paramFlags[0] },
                        { ...createSet("Humidity", data.data.humidity, "#2DD4BF", gradHum), hidden: !paramFlags[1] },
                        { ...createSet("Rainfall", data.data.rainfall, "#3B82F6", null), hidden: !paramFlags[2] },
                        { ...createSet("Wind", data.data.wind, "#8B5CF6", null), hidden: !paramFlags[3] },
                        { ...createSet("Solar", data.data.solar, "#F59E0B", null), hidden: !paramFlags[4] },
                        { ...createSet("Direction", data.data.wind_direction, "#94A3B8", null), hidden: !paramFlags[5] }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    onClick: (evt, activeEls, chartInstance) => {
                        if (!activeEls || activeEls.length === 0) return;

                        const pointIndex = activeEls[0].index;
                        const label = chartInstance?.data?.labels?.[pointIndex];
                        if (!label) return;

                        // Default to 1hr horizon from the timestamp clicked.
                        getForecastForDashboardLabel(label, 1);
                    },
                    plugins: {
                        legend: { 
                            position: 'top', 
                            align: 'end', 
                            labels: { 
                                usePointStyle: true, 
                                boxWidth: 8, 
                                color: '#94A3B8',
                                font: { size: 12 },
                                generateLabels: function(chart) {
                                    const datasets = chart.data.datasets;
                                    const disabledParams = ['Rainfall', 'Wind', 'Direction'];
                                    
                                    return datasets.map((dataset, i) => {
                                        const isDisabled = disabledParams.some(p => dataset.label.includes(p));
                                        return {
                                            text: dataset.label,
                                            fillStyle: isDisabled ? '#9ca3af' : dataset.borderColor,
                                            hidden: !chart.isDatasetVisible(i),
                                            index: i,
                                            pointStyle: 'circle',
                                            strokeStyle: isDisabled ? '#9ca3af' : dataset.borderColor,
                                            lineWidth: 2,
                                            textDecoration: isDisabled ? 'line-through' : undefined,
                                            textColor: isDisabled ? '#9ca3af' : '#94A3B8'
                                        };
                                    });
                                },
                                padding: 15,
                                usePointStyle: true
                            },
                            onClick: function(e, legendItem, legend) {
                                const disabledParams = ['Rainfall', 'Wind', 'Direction'];
                                const dataset = legend.chart.data.datasets[legendItem.index];
                                
                                // Prevent clicking on disabled parameters
                                if (disabledParams.some(p => dataset.label.includes(p))) {
                                    e.stopImmediatePropagation();
                                    return false;
                                }
                                
                                // Allow normal toggle for active parameters
                                const index = legendItem.index;
                                const ci = legend.chart;
                                
                                if (ci.isDatasetVisible(index)) {
                                    ci.hide(index);
                                } else {
                                    ci.show(index);
                                }
                                ci.update();
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.95)',
                            titleColor: '#F8FAFC',
                            bodyColor: '#CBD5E1',
                            borderColor: 'rgba(255,255,255,0.1)',
                            borderWidth: 1,
                            padding: 12,
                            cornerRadius: 12,
                            callbacks: {
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.parsed.y !== null) {
                                        label += context.parsed.y.toFixed(2);
                                    }
                                    return label;
                                }
                            }
                        }
                    },
                    elements: { point: { radius: 0, hitRadius: 10 } },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#64748B' } },
                        y: { border: { display: false }, grid: { borderDash: [4, 4], color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748B', stepSize: 100 } }
                    }
                }
            });

            window.chart = chart;

            // Update graph-based drying summary using the data just plotted
            updateGraphSummary(data.timestamps, data.data);

            // Apply legend styling immediately without delays
            const legendContainer = document.querySelector('.chartjs-legend');
            if (legendContainer) {
                const legendItems = legendContainer.querySelectorAll('li');
                const disabledParams = ['Rainfall', 'Wind', 'Direction'];
                
                legendItems.forEach((item, index) => {
                    const text = item.textContent.trim();
                    const isDisabled = disabledParams.some(p => text.includes(p));
                    
                    if (isDisabled) {
                        item.style.textDecoration = 'line-through';
                        item.style.color = '#9ca3af';
                        item.style.opacity = '0.7';
                        item.style.cursor = 'not-allowed';
                        item.style.pointerEvents = 'none';
                        item.classList.add('disabled-legend-item');
                    } else {
                        item.style.cursor = 'pointer';
                        item.classList.add('active-legend-item');
                    }
                });
            }
        })
        .catch(err => {
            console.error('Error loading dashboard data:', err);
        });
}

function createSet(label, data, color, fillGrad) {
    return {
        label: label,
        data: data,
        borderColor: color,
        backgroundColor: fillGrad || 'transparent',
        fill: !!fillGrad,
        tension: 0.4,
        borderWidth: 2
    }
}

function resetDashboard() {
    // Clear Date Inputs
    const from = document.getElementById('fromDate');
    const to = document.getElementById('toDate');
    if (from) from.value = '';
    if (to) to.value = '';

    // Reset Parameters to Active
    document.querySelectorAll('.checkbox-btn').forEach(btn => btn.classList.add('active'));

    // Load Default View
    loadDashboard(60);
}

function updateDateRange() {
    if (!validateDateRange()) return;
    
    const from = document.getElementById('fromDate').value;
    const to = document.getElementById('toDate').value;
    if (from && to) {
        // Pass the current interval (or default to 60 if no button active)
        const activeBtn = document.querySelector('.time-btn.active');
        const interval = activeBtn ? parseInt(activeBtn.dataset.interval) : 60;
        loadDashboard(interval); // Allow any interval with date range
    }
}

function toggleParam(el, index) {
    // Only allow toggling for Temperature (0), Humidity (1), and Solar Radiation (4)
    const allowedIndices = [0, 1, 4];
    if (!allowedIndices.includes(index)) {
        event.preventDefault();
        event.stopPropagation();
        return false;
    }
    
    el.classList.toggle('active');
    const isVisible = el.classList.contains('active');

    // Toggle Chart Dataset
    if (chart) {
        chart.setDatasetVisibility(index, isVisible);
        chart.update();
    }
}

// Common Gauge Options
const gaugeOptions = {
    width: 140, height: 140, colorPlate: "transparent", colorNeedle: "#F472B6", colorNeedleEnd: "#F472B6",
    colorUnits: "#94A3B8", colorNumbers: "#94A3B8", fontNumbersSize: 20, needleCircleSize: 5,
    needleCircleOuter: true, needleCircleInner: false, animationDuration: 1500, animationRule: "linear",
    borders: false, borderShadowWidth: 0, colorMajorTicks: "#64748B", colorMinorTicks: "#475569",
};

const tempGauge = new RadialGauge({ renderTo: 'tempGauge', ...gaugeOptions, units: "°C", minValue: 0, maxValue: 50, majorTicks: ["0", "10", "20", "30", "40", "50"], colorNeedle: "#F472B6", colorNeedleEnd: "#ec4899", highlights: [] }).draw();
const humidityGauge = new RadialGauge({ renderTo: 'humidityGauge', ...gaugeOptions, units: "%", minValue: 0, maxValue: 100, colorNeedle: "#2DD4BF", colorNeedleEnd: "#14b8a6", highlights: [] }).draw();
const windGauge = new RadialGauge({ renderTo: 'windGauge', ...gaugeOptions, units: "m/s", minValue: 0, maxValue: 20, colorNeedle: "#8B5CF6", colorNeedleEnd: "#7c3aed", highlights: [] }).draw();
const rainGauge = new RadialGauge({ renderTo: 'rainGauge', ...gaugeOptions, units: "mm", minValue: 0, maxValue: 50, colorNeedle: "#3B82F6", colorNeedleEnd: "#2563eb", highlights: [] }).draw();
const solarGauge = new RadialGauge({ renderTo: 'solarGauge', ...gaugeOptions, units: "W/m²", minValue: 0, maxValue: 1000, colorNeedle: "#F59E0B", colorNeedleEnd: "#d97706", highlights: [] }).draw();

function setValue(id, value, gauge) {
    if (gauge) gauge.value = value;
    const el = document.getElementById(id);
    if (el) el.innerText = value;
}

function updateWeatherIcon(temp, humidity, rain, solar) {
    const iconContainer = document.getElementById('weather-icon-display');
    if (!iconContainer) return;
    let iconClass = 'fa-sun'; let label = 'Sunny'; let color = '#F59E0B';
    if (rain > 0.5) { iconClass = 'fa-cloud-showers-heavy'; label = 'Rainy'; color = '#3B82F6'; }
    else if (solar < 200 && temp < 20) { iconClass = 'fa-cloud'; label = 'Cloudy'; color = '#94A3B8'; }
    else if (humidity > 80) { iconClass = 'fa-smog'; label = 'Humid'; color = '#2DD4BF'; }
    else if (temp > 30) { iconClass = 'fa-fire'; label = 'Hot'; color = '#EF4444'; }
    const iconEl = iconContainer.querySelector('i');
    const textEl = iconContainer.querySelector('span');
    if (iconEl && textEl) {
        iconEl.className = `fa-solid ${iconClass}`;
        iconEl.style.color = color;
        textEl.innerText = label;
    }
}

function loadLive() {
    if (Date.now() < ignoreLiveUntil) return;
    fetch("/api/live")
        .then(res => res.json())
        .then(d => {
            setValue("temperature", d.temperature, tempGauge);
            setValue("humidity", d.humidity, humidityGauge);
            setValue("wind_speed", d.wind_speed, windGauge);
            setValue("rainfall", d.rainfall, rainGauge);
            setValue("solar_radiation", d.solar_radiation, solarGauge);
            // Update Direction Text
            const dirEl = document.getElementById("wind_direction");
            if (dirEl) dirEl.innerText = d.wind_direction + "°";
            updateWeatherIcon(d.temperature, d.humidity, d.rainfall, d.solar_radiation);
            updateWeatherSummary();
            const now = new Date();
            const timeEl = document.getElementById("time");
            if (timeEl) timeEl.innerText = `Last updated: ${now.toLocaleTimeString()}`;
        });
}

/* --- Graph-based Drying Suitability Analysis --- */
function _stats(arr) {
    const xs = (arr || []).map(Number).filter(v => !isNaN(v));
    if (!xs.length) return null;
    const sum = xs.reduce((a, b) => a + b, 0);
    const mean = sum / xs.length;
    const min = Math.min(...xs);
    const max = Math.max(...xs);
    const variance = xs.reduce((a, b) => a + (b - mean) ** 2, 0) / xs.length;
    const std = Math.sqrt(variance);
    // Linear trend slope (per-sample)
    let slope = 0;
    if (xs.length > 1) {
        const n = xs.length;
        const meanX = (n - 1) / 2;
        let num = 0, den = 0;
        for (let i = 0; i < n; i++) {
            num += (i - meanX) * (xs[i] - mean);
            den += (i - meanX) ** 2;
        }
        slope = den === 0 ? 0 : num / den;
    }
    const trendTotal = slope * (xs.length - 1);
    return { mean, min, max, std, slope, trendTotal, n: xs.length };
}

function _trendWord(total, unit, threshold) {
    if (Math.abs(total) < threshold) return `stable (≈${total >= 0 ? '+' : ''}${total.toFixed(1)}${unit})`;
    return total > 0
        ? `rising (+${total.toFixed(1)}${unit} across the window)`
        : `falling (${total.toFixed(1)}${unit} across the window)`;
}

function _scoreDrying(tempStats, humStats, solarStats) {
    // Each sub-score 0..100
    const t = tempStats?.mean ?? 0;
    const h = humStats?.mean ?? 0;
    const s = solarStats?.mean ?? 0;

    // Temperature: optimal 28-38°C
    let ts;
    if (t < 15) ts = 10;
    else if (t < 22) ts = 40;
    else if (t < 28) ts = 70;
    else if (t <= 38) ts = 100;
    else if (t <= 42) ts = 75;
    else ts = 50;

    // Humidity: lower is better, optimal < 50%
    let hs;
    if (h < 40) hs = 100;
    else if (h < 55) hs = 85;
    else if (h < 70) hs = 60;
    else if (h < 80) hs = 35;
    else hs = 15;

    // Solar: higher is better
    let ss;
    if (s > 600) ss = 100;
    else if (s > 450) ss = 85;
    else if (s > 300) ss = 65;
    else if (s > 150) ss = 40;
    else if (s > 50) ss = 20;
    else ss = 5;

    // Weighted: humidity is the biggest enemy of drying
    const overall = Math.round(0.30 * ts + 0.45 * hs + 0.25 * ss);
    return { overall, temp: ts, hum: hs, solar: ss };
}

function _verdict(score) {
    if (score >= 80) return { word: "Excellent", emoji: "✅", color: "#10B981",
        text: "Conditions across the selected period look great for drying. You can dry with confidence." };
    if (score >= 65) return { word: "Good", emoji: "👍", color: "#22C55E",
        text: "Conditions are favorable for drying. Expect normal drying times." };
    if (score >= 45) return { word: "Moderate", emoji: "⚠️", color: "#F59E0B",
        text: "Conditions are workable but not ideal. Drying will be slower; check the produce more often." };
    if (score >= 25) return { word: "Poor", emoji: "🚫", color: "#F97316",
        text: "Conditions are weak for natural drying. Consider supplemental heat or wait for a better window." };
    return { word: "Unsuitable", emoji: "❌", color: "#EF4444",
        text: "Conditions are unsuitable for natural drying right now. Use a controlled dryer or postpone." };
}

function generateGraphSummary(timestamps, data) {
    const tempStats = _stats(data?.temperature);
    const humStats = _stats(data?.humidity);
    const solarStats = _stats(data?.solar);

    if (!tempStats || !humStats || !solarStats) {
        return {
            header: `<span style="opacity:0.7;">Not enough data in the selected timeframe to analyze.</span>`,
            body: ""
        };
    }

    const score = _scoreDrying(tempStats, humStats, solarStats);
    const verdict = _verdict(score.overall);

    const periodLabel = timestamps && timestamps.length
        ? `${timestamps[0]} → ${timestamps[timestamps.length - 1]} (${tempStats.n} samples)`
        : `${tempStats.n} samples`;

    // Header (always visible) - verdict + score
    const header = `
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:1.1rem;">${verdict.emoji}</span>
            <strong style="color:${verdict.color}; font-size:0.95rem;">${verdict.word} for drying</strong>
            <span style="margin-left:auto; font-size:0.75rem; opacity:0.7; white-space:nowrap;">Score ${score.overall}/100</span>
        </div>
    `;

    // Plain-English per-metric reading
    const tempPhrase = tempStats.mean >= 28 && tempStats.mean <= 38
        ? "in the sweet spot"
        : tempStats.mean < 22 ? "on the cool side"
        : tempStats.mean < 28 ? "a bit low"
        : tempStats.mean > 42 ? "very hot — watch product quality" : "warm";

    const humPhrase = humStats.mean < 40 ? "very dry — excellent"
        : humStats.mean < 55 ? "comfortably dry"
        : humStats.mean < 70 ? "a bit humid — slower drying"
        : humStats.mean < 80 ? "humid — drying will struggle"
        : "very humid — natural drying not recommended";

    const solarPhrase = solarStats.mean > 600 ? "strong sun"
        : solarStats.mean > 300 ? "decent sun"
        : solarStats.mean > 100 ? "weak sun" : "little to no sun (likely night/cloud)";

    // Body (revealed when expanded) - explanation + details + technical breakdown
    const body = `
        <div style="margin: 8px 0 10px 0;">${verdict.text}</div>
        <div style="font-size:0.76rem; opacity:0.8; margin-bottom:8px;">
            <strong>Period:</strong> ${periodLabel}
        </div>
        <div style="font-size:0.78rem; line-height:1.6;">
            🌡️ Temperature is <strong>${tempPhrase}</strong> (${tempStats.mean.toFixed(1)}°C avg, ${_trendWord(tempStats.trendTotal, '°C', 1.5)}).<br>
            💧 Humidity is <strong>${humPhrase}</strong> (${humStats.mean.toFixed(1)}% avg, ${_trendWord(humStats.trendTotal, '%', 3)}).<br>
            ☀️ Solar input is <strong>${solarPhrase}</strong> (${solarStats.mean.toFixed(0)} W/m² avg).
        </div>
        <div style="margin-top:10px; padding-top:8px; border-top:1px dashed rgba(148,163,184,0.25); font-size:0.72rem; opacity:0.85;">
            <div style="font-weight:600; margin-bottom:4px;">📐 Technical breakdown</div>
            <div>Temp — min ${tempStats.min.toFixed(1)} / max ${tempStats.max.toFixed(1)} / σ ${tempStats.std.toFixed(2)} °C</div>
            <div>Humidity — min ${humStats.min.toFixed(1)} / max ${humStats.max.toFixed(1)} / σ ${humStats.std.toFixed(2)} %</div>
            <div>Solar — min ${solarStats.min.toFixed(0)} / max ${solarStats.max.toFixed(0)} / σ ${solarStats.std.toFixed(1)} W/m²</div>
            <div style="margin-top:4px;">Sub-scores → T:${score.temp} H:${score.hum} S:${score.solar} (weighted 30/45/25)</div>
        </div>
    `;

    return { header, body };
}

function updateGraphSummary(timestamps, data) {
    const headerEl = document.getElementById('weatherSummaryHeader');
    const bodyEl = document.getElementById('weatherSummaryBody');
    const legacyEl = document.getElementById('weatherSummaryText');     // backwards compat
    const paramEl = document.getElementById('parameterSummaryText');    // backwards compat

    const { header, body } = generateGraphSummary(timestamps, data);

    if (headerEl) headerEl.innerHTML = header;
    if (bodyEl) bodyEl.innerHTML = body;
    if (legacyEl) legacyEl.innerHTML = header + body;
    if (paramEl) paramEl.innerHTML = header + body;
}

// Backwards-compatible no-op so older call sites don't error
function updateWeatherSummary() { /* superseded by updateGraphSummary */ }

/* --- Date Validation --- */
function setupDateValidation() {
    const fromDateInput = document.getElementById('fromDate');
    const toDateInput = document.getElementById('toDate');
    const isForecasting = isForcastingPage();
    
    if (!fromDateInput || !toDateInput) return;
    
    const today = new Date().toISOString().split('T')[0];
    
    if (isForecasting) {
        // Forecasting: only future dates allowed
        fromDateInput.min = today;
        toDateInput.min = today;
        fromDateInput.value = today;
        toDateInput.value = today;
    } else {
        // Dashboard: From date can be any past date (no HTML max constraint)
        // Only JavaScript validation will enforce the constraint
        toDateInput.max = today;
        toDateInput.value = today;
    }
}

function validateDateRange() {
    const from = document.getElementById('fromDate').value;
    const to = document.getElementById('toDate').value;
    const isForecasting = isForcastingPage();
    
    if (!from || !to) return true;
    
    // Parse dates without time component to avoid timezone issues
    const fromDate = new Date(from + 'T00:00:00').getTime();
    const toDate = new Date(to + 'T00:00:00').getTime();
    const todayTime = new Date(new Date().toISOString().split('T')[0] + 'T00:00:00').getTime();
    
    if (isForecasting) {
        // For forecasting: both dates should be >= today
        if (fromDate < todayTime || toDate < todayTime) {
            alert("Invalid date selection. Forecasting allows only current and future dates.");
            if (fromDate < todayTime) document.getElementById('fromDate').value = '';
            return false;
        }
    } else {
        // For dashboard: From date must be STRICTLY PAST (before today), To date can be today
        if (fromDate >= todayTime) {
            alert("Invalid date selection. 'From Date' must be a date in the past, not current or future.");
            document.getElementById('fromDate').value = '';
            return false;
        }
        if (toDate > todayTime) {
            alert("Invalid date selection. 'To Date' cannot be a future date.");
            document.getElementById('toDate').value = new Date().toISOString().split('T')[0];
            return false;
        }
    }
    
    // Check from date is not after to date
    if (fromDate > toDate) {
        alert("Invalid date range. 'From Date' must be before or equal to 'To Date'.");
        return false;
    }
    
    return true;
}

function toggleDisabledParam(event) {
    event.preventDefault();
    event.stopPropagation();
    return false;
}

function toggleDark() {
    document.body.classList.toggle("dark");
    // Reload chart with current active button interval
    const activeBtn = document.querySelector('.time-btn.active');
    const interval = activeBtn ? parseInt(activeBtn.dataset.interval) : 60;
    loadDashboard(interval);
}

// Initial Load
document.addEventListener('DOMContentLoaded', function() {
    setupDateValidation();
    updateWeatherSummary();
    setupTimeButtonListeners();
});

function setupTimeButtonListeners() {
    // Use document-level event delegation with bubble phase (more reliable)
    // This works even if the .controls container changes or rerenders
    document.removeEventListener('click', handleTimeButtonClick, false);
    document.addEventListener('click', handleTimeButtonClick, false);
    console.log('Time button listeners attached');
}

function handleTimeButtonClick(e) {
    // Check if clicked element or any parent is a .time-btn
    const btn = e.target.closest('.time-btn');
    if (!btn) return;
    
    // Prevent default behavior
    e.preventDefault();
    e.stopPropagation();
    
    // Extract interval value
    const intervalStr = btn.getAttribute('data-interval');
    const interval = parseInt(intervalStr, 10);
    
    // Validate and call loadDashboard
    if (!isNaN(interval)) {
        console.log('Time button clicked:', btn.textContent.trim(), '- Interval:', interval);
        loadDashboard(interval);
    }
}

setInterval(loadLive, 3000);
loadDashboard(60);
loadLive();



function toggleNotifs() {
    alert("🔔 Notifications:\n1. Rain predicted at 16:00 (Accuracy: 85%)\n2. Filter maintenance due in 2 days.");
}
