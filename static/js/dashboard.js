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
                        y: { border: { display: false }, grid: { borderDash: [4, 4], color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748B' } }
                    }
                }
            });

            window.chart = chart;
            
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

/* --- Weather Summary Generation --- */
function generateWeatherSummary(temp, humidity, solar) {
    // Create detailed summary with condition assessment
    let assessment = "📊 <strong>Environmental Assessment:</strong> ";
    let condition = "";
    
    // Determine overall condition based on solar radiation
    if (solar > 600) {
        condition = "favorable";
    } else if (solar >= 400 && solar <= 600) {
        condition = "moderate";
    } else {
        condition = "poor";
    }
    
    assessment += "Conditions are " + condition + " for drying. ";
    
    // Add detailed parameters
    assessment += "<br>🌡️ <strong>Temperature:</strong> " + temp + "°C (";
    if (temp < 15) {
        assessment += "too cold, drying will be slow";
    } else if (temp < 25) {
        assessment += "acceptable, but could be warmer";
    } else if (temp < 35) {
        assessment += "ideal for drying";
    } else {
        assessment += "high, monitor product quality";
    }
    assessment += ") ";
    
    assessment += "<br>💧 <strong>Humidity:</strong> " + humidity + "% (";
    if (humidity < 40) {
        assessment += "excellent for drying";
    } else if (humidity < 60) {
        assessment += "good drying conditions";
    } else if (humidity < 75) {
        assessment += "moderate, acceptable";
    } else {
        assessment += "high, increase ventilation";
    }
    assessment += ") ";
    
    assessment += "<br>☀️ <strong>Solar Radiation:</strong> " + solar + " W/m² (";
    if (solar > 600) {
        assessment += "excellent natural drying power";
    } else if (solar > 400) {
        assessment += "good solar input";
    } else if (solar > 200) {
        assessment += "moderate, supplement with heat";
    } else {
        assessment += "low, consider artificial drying";
    }
    assessment += ")";
    
    return assessment;
}

function updateWeatherSummary() {
    const summaryEl = document.getElementById('weatherSummaryText');
    const paramSummaryEl = document.getElementById('parameterSummaryText');
    
    const temp = parseFloat(document.getElementById('temperature')?.innerText) || 0;
    const humidity = parseFloat(document.getElementById('humidity')?.innerText) || 0;
    const solar = parseFloat(document.getElementById('solar_radiation')?.innerText) || 0;
    
    if (temp && humidity && solar) {
        const summary = generateWeatherSummary(temp, humidity, solar);
        
        // Update both summary elements
        if (summaryEl) summaryEl.innerHTML = summary;
        if (paramSummaryEl) paramSummaryEl.innerHTML = summary;
    }
}

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
setInterval(updateWeatherSummary, 5000);
loadDashboard(60);
loadLive();



function toggleNotifs() {
    alert("🔔 Notifications:\n1. Rain predicted at 16:00 (Accuracy: 85%)\n2. Filter maintenance due in 2 days.");
}

/* --- DryBot Chat Logic --- */
function toggleChat() {
    const win = document.getElementById('dryBotWindow');
    const badge = document.querySelector('.bot-notification-toolbar');
    const altBadge = document.querySelector('.bot-notification');
    
    if (!win) return;
    
    win.classList.toggle('open');
    
    if (win.classList.contains('open')) {
        if (badge) badge.style.display = 'none';
        if (altBadge) altBadge.style.display = 'none';
        // Focus on input when chat opens
        setTimeout(() => {
            const input = document.getElementById('userMsg');
            if (input) input.focus();
        }, 300);
    }
}

function handleChat(e) { 
    if (e.key === 'Enter') sendChat(); 
}

function sendChat() {
    const input = document.getElementById('userMsg');
    if (!input) return;
    
    const txt = input.value.trim();
    if (!txt) return;
    
    addMsg(txt, 'user');
    input.value = '';
    
    // Send request to backend API
    fetch('/api/chatbot', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: txt })
    })
    .then(res => res.json())
    .then(data => {
        const reply = data.response || "I couldn't process that. Please try again.";
        addMsg(reply, 'bot');
    })
    .catch(err => {
        console.error('Chatbot error:', err);
        addMsg("Sorry, I encountered an error. Please try again.", 'bot');
    });
}

function addMsg(txt, sender) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const div = document.createElement('div');
    div.classList.add('msg', sender);
    div.innerHTML = txt;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function getBotResponse(input) {
    input = input.toLowerCase().trim();
    
    // Get current values from dashboard
    const temp = parseFloat(document.getElementById('temperature')?.innerText) || 0;
    const humidity = parseFloat(document.getElementById('humidity')?.innerText) || 0;
    const solar = parseFloat(document.getElementById('solar_radiation')?.innerText) || 0;
    const rain = parseFloat(document.getElementById('rainfall')?.innerText) || 0;
    const wind = parseFloat(document.getElementById('wind_speed')?.innerText) || 0;
    
    // ========== GREETING QUERIES ==========
    if (input.match(/^(hello|hi|hey|greetings|good morning|good afternoon)/)) {
        return "👋 Hello! I'm DryBot, your drying assistant. I can help you monitor and optimize your drying operations. Ask me about current conditions, drying recommendations, or environmental parameters!";
    }
    
    // ========== GENERAL STATUS QUERIES ==========
    if (input.includes('status') || input.includes('how are you') || input.includes('what is happening')) {
        return "✅ All systems monitoring normally! Current session active with live sensor data. Temperature: " + temp + "°C, Humidity: " + humidity + "%. Ready to assist with any drying questions!";
    }
    
    // ========== TEMPERATURE QUERIES ==========
    if (input.includes('temperature') || input.includes('temp') || input.includes('hot') || input.includes('cold')) {
        let tempAdvice = `🌡️ <strong>Current Temperature: ${temp}°C</strong><br>`;
        if (temp < 15) {
            tempAdvice += "⚠️ Temperature is too cold for efficient drying. Temperature below 15°C significantly slows the drying process. Consider increasing heat input or waiting for warmer conditions.";
        } else if (temp < 25) {
            tempAdvice += "✓ Temperature is acceptable but could be improved. The range 25-35°C is ideal for most drying applications. Current conditions will allow moderate drying speed.";
        } else if (temp < 35) {
            tempAdvice += "✓✓ Excellent temperature for drying! This range (25-35°C) is ideal for most agricultural products. Optimal drying speed with minimal product damage risk.";
        } else if (temp < 45) {
            tempAdvice += "⚠️ Temperature is getting high. While drying will be faster, monitor product quality closely to prevent over-drying or heat damage.";
        } else {
            tempAdvice += "⚠️ Temperature is too high! Risk of product damage and nutrient loss. Reduce heat input or pause drying to protect product quality.";
        }
        return tempAdvice;
    }
    
    // ========== HUMIDITY QUERIES ==========
    if (input.includes('humidity') || input.includes('moist') || input.includes('moisture') || input.includes('humid')) {
        let humidityAdvice = `💧 <strong>Current Humidity: ${humidity}%</strong><br>`;
        if (humidity < 30) {
            humidityAdvice += "✓✓ Excellent! Very low humidity provides ideal conditions for rapid, efficient drying. Moisture will evaporate quickly.";
        } else if (humidity < 50) {
            humidityAdvice += "✓ Good drying conditions. Low humidity supports effective moisture removal. Drying speed is favorable.";
        } else if (humidity < 70) {
            humidityAdvice += "✓ Moderate conditions - acceptable for drying but not optimal. Increase ventilation or use heating to improve drying rate.";
        } else if (humidity < 85) {
            humidityAdvice += "⚠️ High humidity detected. This slows drying significantly and increases mold/disease risk. Increase ventilation, heating, or airflow urgently.";
        } else {
            humidityAdvice += "⚠️ Critical! Very high humidity will prevent effective drying and cause product spoilage. Take immediate action: increase ventilation, add heat, reduce product load.";
        }
        return humidityAdvice;
    }
    
    // ========== SOLAR RADIATION QUERIES ==========
    if (input.includes('solar') || input.includes('sun') || input.includes('radiation') || input.includes('light') || input.includes('sunlight')) {
        let solarAdvice = `☀️ <strong>Solar Radiation: ${solar} W/m²</strong><br>`;
        if (solar > 800) {
            solarAdvice += "✓✓ Exceptional! Very high solar intensity - excellent natural drying power. Maximize open-air or solar drying operations.";
        } else if (solar > 600) {
            solarAdvice += "✓ Ideal solar conditions! Strong natural drying force available. Good conditions for solar or passive drying systems.";
        } else if (solar > 400) {
            solarAdvice += "✓ Good solar input. Adequate for solar-aided drying. Combined with heating, conditions are suitable for drying.";
        } else if (solar > 200) {
            solarAdvice += "✓ Moderate solar conditions. Consider supplemental heating or active ventilation to improve drying rate.";
        } else if (solar > 50) {
            solarAdvice += "⚠️ Low solar radiation. Natural drying is slow. Use supplemental heat sources or move to covered, ventilated drying area.";
        } else {
            solarAdvice += "⚠️ Very low/no solar radiation (nighttime or cloudy). Active drying with heat source required for efficient moisture removal.";
        }
        return solarAdvice;
    }
    
    // ========== WEATHER/CONDITIONS ASSESSMENT ==========
    if (input.includes('weather') || input.includes('condition') || input.includes('suitable') || input.includes('environment') || input.includes('assessment')) {
        const summary = generateWeatherSummary(temp, humidity, solar);
        return "🌤️ <strong>Overall Environmental Assessment:</strong><br>" + summary + 
               "<br><br>📊 Key Metrics: Temp=" + temp + "°C | Humidity=" + humidity + "% | Solar=" + solar + " W/m²";
    }
    
    // ========== DRYING TIMELINE/DURATION ==========
    if (input.includes('how long') || input.includes('duration') || input.includes('take') || input.includes('time to dry') || input.includes('drying time')) {
        let timeAdvice = "⏱️ <strong>Estimated Drying Duration:</strong><br>";
        // Base estimate: 12-48 hours depending on conditions
        let dryingHours = 48;
        
        if (temp > 30 && humidity < 50 && solar > 600) {
            dryingHours = 12;
            timeAdvice += "🟢 Fast drying: <strong>~12-24 hours</strong> - Excellent conditions!";
        } else if (temp > 25 && humidity < 60 && solar > 400) {
            dryingHours = 24;
            timeAdvice += "🟢 Normal drying: <strong>~24-36 hours</strong> - Good conditions.";
        } else if (temp > 20 && humidity < 70) {
            dryingHours = 36;
            timeAdvice += "🟡 Moderate drying: <strong>~36-48 hours</strong> - Acceptable conditions.";
        } else {
            dryingHours = 48;
            timeAdvice += "🔴 Slow drying: <strong>~48+ hours</strong> - Suboptimal conditions. Recommend improvements.";
        }
        timeAdvice += "<br><em>Note: Actual time depends on product type, thickness, and initial moisture content. This is a general estimate.</em>";
        return timeAdvice;
    }
    
    // ========== RECOMMENDATIONS FOR IMPROVEMENT ==========
    if (input.includes('recommend') || input.includes('advice') || input.includes('improve') || input.includes('optimize') || input.includes('better') || input.includes('what should i do')) {
        let recommendation = "💡 <strong>Optimization Recommendations:</strong><br>";
        const suggestions = [];
        
        if (temp < 25) suggestions.push("🔴 Increase temperature (currently " + temp + "°C, target 25-35°C)");
        if (humidity > 60) suggestions.push("🔴 Reduce humidity (currently " + humidity + "%, target <60%)");
        if (solar < 400) suggestions.push("🔴 Increase airflow or add heating (solar currently " + solar + " W/m²)");
        if (wind < 1) suggestions.push("🟡 Increase ventilation to improve air circulation");
        
        if (suggestions.length === 0) {
            recommendation += "✓ Current conditions are already optimal for drying! Maintain current settings and continue monitoring.";
        } else {
            recommendation += suggestions.join("<br>");
        }
        
        return recommendation;
    }
    
    // ========== SPECIFIC WARNINGS/ALERTS ==========
    if (input.includes('warning') || input.includes('problem') || input.includes('alert') || input.includes('risk') || input.includes('issue')) {
        let alerts = [];
        if (temp > 40) alerts.push("⚠️ HIGH: Temperature critical - risk of product damage");
        if (humidity > 75) alerts.push("⚠️ HIGH: Humidity critical - mold/contamination risk");
        if (rain > 2) alerts.push("⚠️ MEDIUM: Rainfall detected - protect product");
        if (temp < 10) alerts.push("⚠️ MEDIUM: Temperature too low - drying very slow");
        
        if (alerts.length === 0) {
            return "✓ No critical alerts. System parameters within acceptable ranges.";
        }
        return "🚨 <strong>Current Alerts:</strong><br>" + alerts.join("<br>");
    }
    
    // ========== SYSTEM HELP/HOW TO USE ==========
    if (input.includes('help') || input.includes('how to') || input.includes('what can you') || input.includes('explain') || input.includes('tell me about')) {
        return "ℹ️ <strong>How I Can Help:</strong><br>" +
               "📊 <strong>Current Data:</strong> Ask about temperature, humidity, solar radiation, or weather conditions<br>" +
               "⏱️ <strong>Drying Time:</strong> Ask 'How long will drying take?'<br>" +
               "💡 <strong>Recommendations:</strong> Ask for optimization advice<br>" +
               "🚨 <strong>Alerts:</strong> Ask about warnings or problems<br>" +
               "🌤️ <strong>Overall Status:</strong> Ask about environmental assessment<br>" +
               "<em>Be specific for better recommendations!</em>";
    }
    
    // ========== DEFAULT RESPONSE ==========
    return "🤔 I didn't quite understand that. Try asking me about:<br>" +
           "• Temperature, humidity, or solar radiation<br>" +
           "• Current drying conditions<br>" +
           "• How long drying will take<br>" +
           "• Optimization recommendations<br>" +
           "• Any warnings or alerts<br>" +
           "Type 'help' for more options!";
}
