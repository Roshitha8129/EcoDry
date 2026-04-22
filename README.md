# EcoDry - Smart Food Drying System

## 📋 Project Overview

EcoDry is a comprehensive **Smart Food Drying System** that leverages real-time environmental data and machine learning to provide intelligent drying process management. The system acts as a digital twin for agricultural drying operations, offering real-time monitoring, predictive analytics, and AI-driven recommendations.

**Key Features:**
- 🌡️ Real-time sensor monitoring (Temperature, Humidity, Solar Radiation, Wind)
- 📊 Interactive dashboards with responsive design
- 🤖 ML-powered weather forecasting (XGBoost models)
- 🌍 Fully responsive design (mobile, tablet, desktop)
- 📱 Touch-friendly interface with accessibility support
- 🔄 Date range data analysis with environmental assessment
- 💬 Intelligent chatbot assistant (DryBot)

---

## 🏗️ Architecture

The project follows **Flask best practices** with a clean, modular architecture:

```
app/
├── __init__.py           # App factory pattern
├── routes/
│   ├── __init__.py      
│   ├── pages.py         # HTML page routes
│   └── api.py           # API endpoints
├── services/
│   ├── data_service.py      # Dashboard & data retrieval
│   ├── forecast_service.py  # ML predictions
│   └── summary_service.py   # Environmental assessment
└── utils/
    └── __init__.py          # Helper utilities

backend/
├── weather_backend.py        # Legacy backend (kept for compatibility)
├── updated_sensor_data.csv   # Single source of truth for sensor data
└── [model JSON files]        # XGBoost models

templates/               # HTML templates
static/
├── css/                # Stylesheets
└── js/                 # JavaScript
```

---

## 🚀 Technology Stack

### Backend
- **Framework**: Flask 2.3.2
- **Data Processing**: Pandas, NumPy
- **ML Models**: XGBoost 1.7.5 (JSON format)
- **ML Tools**: scikit-learn, joblib
- **Python**: 3.8+

### Frontend
- **Structure**: HTML5 (Semantic)
- **Styling**: CSS3 (Responsive, Mobile-first)
- **Scripting**: JavaScript ES6+
- **Charts**: Chart.js (Interactive visualizations)
- **Gauges**: Canvas Gauges (Live metrics)
- **Icons**: FontAwesome
- **Fonts**: Google Fonts (Inter)

---

## 📱 Responsive Design

Fully responsive across all devices:

| Breakpoint | Device | Layout |
|-----------|--------|--------|
| 320px–480px | Mobile | Single column, optimized touch |
| 481px–768px | Mobile landscape/tablets | Flexible 2-column |
| 769px–1024px | Tablets | Multi-column grids |
| 1025px–1200px | Desktops | Full layouts |
| 1201px+ | Large screens | Optimized spacing |

**Features:**
- Mobile-first design approach
- Touch-friendly buttons (min 44px)
- No horizontal scrolling
- Proportional text scaling
- Dark/Light mode support

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.8+
- pip package manager
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Step 1: Clone or Extract
```bash
cd updated_inte_pro
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Verify Setup
```bash
pip list
```

---

## 🏃 Running the Application

### Method 1: Direct Python (Recommended)
```bash
python app.py
```

### Method 2: Flask CLI
```bash
flask run
```

### Method 3: Custom Port
```bash
python app.py
# Set PORT environment variable
# Windows: set PORT=8000
# Linux/Mac: export PORT=8000
```

### Access the Application
- **Home**: http://127.0.0.1:7860
- **Dashboard**: http://127.0.0.1:7860/dashboard
- **Forecasting**: http://127.0.0.1:7860/forecasting
- **Settings**: http://127.0.0.1:7860/settings
- **About**: http://127.0.0.1:7860/about

---

## 🔌 API Endpoints

### Live Data
**`GET /api/live`**
Returns current sensor readings.

```json
{
  "temperature": 28.5,
  "humidity": 65.2,
  "rainfall": 0.0,
  "wind_speed": 2.3,
  "solar_radiation": 450.8,
  "wind_direction": 180,
  "time": "14:30"
}
```

### Dashboard Data
**`GET /api/dashboard`**

Query Parameters:
- `interval`: Time interval in minutes (default: 60)
- `start_date`: Optional, YYYY-MM-DD format
- `end_date`: Optional, YYYY-MM-DD format

```json
{
  "timestamps": ["09:00", "10:00", "11:00"],
  "data": {
    "temperature": [25.0, 26.5, 28.0],
    "humidity": [60, 58, 55],
    "rainfall": [0, 0, 0],
    "wind": [1.5, 2.0, 2.5],
    "solar": [300, 400, 500],
    "wind_direction": [180, 185, 190]
  }
}
```

### Weather Forecast
**`GET /api/forecast`**

Query Parameters:
- `date`: YYYY-MM-DD
- `time`: HH:MM (12-hour format)
- `am_pm`: AM or PM
- `horizon`: Hours ahead (1, 4, or 24)

```json
{
  "temperature": 29.5,
  "humidity": 62.0,
  "solar_radiation": 520.0,
  "rainfall": 0.0,
  "wind_speed": 2.1,
  "wind_direction": 185
}
```

### Environmental Summary
**`GET /api/summary`**

Query Parameters:
- `start_date`: YYYY-MM-DD (required)
- `end_date`: YYYY-MM-DD (required)
- `interval`: Minutes (default: 60)

```json
{
  "temperature": {
    "value": 27.5,
    "unit": "°C",
    "status": "ideal"
  },
  "humidity": {
    "value": 62.5,
    "unit": "%",
    "status": "moderate"
  },
  "solar_radiation": {
    "value": 450.0,
    "unit": "W/m²",
    "status": "moderate"
  },
  "suitability": "Moderately suitable",
  "assessment": "Temperature is optimal... | Low humidity is ideal..."
}
```

---

## 📊 Dashboard Features

### Live Monitoring
- **Animated Gauges**: Real-time visualization of:
  - Temperature (°C)
  - Humidity (%)
  - Solar Radiation (W/m²)
  - Wind Speed (m/s)

### Historical Charts
- Interactive line charts with date range selection
- Automatic data downsampling for optimal performance
- Multiple metric visualization
- Responsive scaling

### Environmental Assessment
- **Trend-based Summary**: Analyzes selected date range
- **Suitability Rating**: Evaluates drying conditions
- **Actionable Insights**: Provides recommendations

#### Assessment Logic

**Temperature Evaluation:**
- < 25°C → Low (may slow drying)
- 25–35°C → Ideal
- > 35°C → High (monitor integrity)

**Humidity Assessment:**
- < 40% → Good for drying
- 40–70% → Moderate
- > 70% → Not suitable

**Solar Radiation:**
- < 300 W/m² → Low
- 300–600 W/m² → Moderate
- > 600 W/m² → Excellent

**Drying Suitability:**
- **Favorable** → Most conditions optimal
- **Moderately Suitable** → Mixed conditions
- **Not Suitable** → Poor conditions

---

## 🤖 DryBot Chatbot

### Features
- 💬 Intelligent question answering
- 📊 Real-time sensor data integration
- 🌧️ Rain prediction alerts
- 💡 Drying recommendations
- ⚡ Energy status reporting

### Available on
- Dashboard page
- Forecasting page

---

## 🔒 Configuration

### Environment Variables
```bash
# Set custom port (default 7860)
set PORT=8080

# Debug mode (not recommended for production)
set FLASK_ENV=production
```

### App Configuration (`app/__init__.py`)
- `JSON_SORT_KEYS`: Disabled for response consistency
- `template_folder`: Points to templates/
- `static_folder`: Points to static/

---

## 📁 Project Structure

### Root Level
```
updated_inte_pro/
├── app.py                  # Entry point
├── requirements.txt        # Dependencies
├── README.md              # This file
│
├── updated_inte_pro/
│   └── inte/              # Main application
│       ├── app/           # Application modules
│       ├── backend/       # ML models & data
│       ├── templates/     # HTML files
│       ├── static/        # CSS, JS, assets
│       └── app.py         # App launcher
```

---

## 🧪 Testing

### Quick Test
```bash
# In browser, visit:
http://127.0.0.1:7860

# Test API endpoints:
http://127.0.0.1:7860/api/live
http://127.0.0.1:7860/api/dashboard?interval=60
```

### Debug Mode
For development only:
```python
# In app.py, change:
app.run(host="0.0.0.0", port=port, debug=True)
```

---

## 🚀 Deployment

### Hugging Face Spaces
1. Set `PORT=7860` in environment
2. Ensure `requirements.txt` is current
3. App will start automatically
4. Access via Hugging Face URL

### Docker (Optional)
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

### Traditional Hosting
1. Ensure Python 3.8+ installed
2. Install dependencies
3. Set appropriate PORT
4. Run `python app.py`

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Windows: Find process using port 7860
netstat -ano | findstr :7860

# macOS/Linux: Find process
lsof -i :7860

# Kill process and retry
```

### Module Not Found
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Verify installation
python -c "import flask; print(flask.__version__)"
```

### Data Not Loading
1. Check `backend/updated_sensor_data.csv` exists
2. Verify CSV files are present
3. Check file paths in `DataService`
4. Review console for error messages

### Charts Not Displaying
1. Clear browser cache
2. Check browser console for JS errors
3. Verify `/api/dashboard` returns valid data
4. Check Chart.js is loaded

---

## 📚 Code Quality

### PEP 8 Compliance
- Proper naming conventions
- Documented functions with docstrings
- 80-character line limits
- Type hints where beneficial

### Architecture Benefits
- **Modular**: Easy to extend and test
- **Scalable**: Services can be enhanced independently
- **Maintainable**: Clear separation of concerns
- **Production-ready**: Error handling throughout

---

## 📖 File Guide

| File | Purpose |
|------|---------|
| `app/__init__.py` | App factory with blueprint registration |
| `app/routes/pages.py` | HTML page routes |
| `app/routes/api.py` | API endpoints |
| `app/services/data_service.py` | Data retrieval & processing |
| `app/services/forecast_service.py` | ML predictions |
| `app/services/summary_service.py` | Environmental assessment |
| `app/utils/__init__.py` | Helper functions |
| `backend/weather_backend.py` | Legacy backend (compatibility) |
| `templates/*.html` | Frontend pages |
| `static/css/*.css` | Stylesheets |
| `static/js/*.js` | Client-side logic |

---

## 🔄 Future Enhancements

- [ ] User authentication & profiles
- [ ] Data persistence (database)
- [ ] Advanced ML models
- [ ] Mobile app (React Native)
- [ ] Real IoT sensor integration
- [ ] Historical data export (CSV/PDF)
- [ ] Batch processing optimization
- [ ] Real-time notifications

---

## 📝 License

This project is provided as-is for educational and research purposes.

---

## 🤝 Support

For issues or questions:
1. Check troubleshooting section
2. Review console logs
3. Verify all dependencies installed
4. Ensure correct Python version (3.8+)

---

## 📅 Last Updated
2026 | Refactored with clean architecture

---

**Status**: ✅ Production Ready | 🟢 All Features Active | 📊 ML Models Integrated
```

### Data Files Missing
Ensure `backend/updated_sensor_data.csv` exists. Expected columns:
`S.No., Date and Time, Temperature, RH, Solar Radiation`

## Project Directory Structure
```
inte/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── backend/
│   ├── weather_backend.py          # Core data processing logic
│   └── data/                       # CSV data files
├── templates/                      # HTML pages
│   ├── home.html
│   ├── dashboard.html
│   ├── settings.html
│   ├── about.html
│   └── ...
└── static/
    ├── css/                        # Stylesheets
    └── js/                         # JavaScript files
```
