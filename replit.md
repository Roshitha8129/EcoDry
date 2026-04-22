# EcoDry - Smart Food Drying System

## Overview
EcoDry is a Smart Food Drying System that provides real-time monitoring and predictive analytics for agricultural drying processes. It functions as a digital twin for drying operations, using machine learning (XGBoost) to forecast weather conditions and provide drying recommendations.

## Architecture

### Backend
- **Framework:** Flask 2.x (App Factory pattern with Blueprints)
- **ML:** XGBoost, scikit-learn, pandas/numpy
- **Entry point:** `app.py`
- **App factory:** `app/__init__.py`
- **Routes:** `app/routes/` (api.py, pages.py)
- **Services:** `app/services/` (forecast_service.py, data_service.py)
- **Data & Models:** `backend/` (CSV datasets, JSON XGBoost model files)

### Frontend
- Plain HTML5/CSS3 with Jinja2 templates
- Chart.js for visualizations
- Canvas Gauges for real-time metrics
- Templates in `templates/`
- Static assets in `static/`

## Key API Endpoints
- `GET /` - Home page
- `GET /dashboard` - Main dashboard
- `GET /api/live` - Live sensor data
- `GET /api/forecast` - ML weather forecast
- `GET /api/summary` - Summary data
- `GET /api/dashboard` - Dashboard data

## Running the App
- **Dev:** `python app.py` (runs on port 5000)
- **Production:** `gunicorn --bind=0.0.0.0:5000 --reuse-port app:app`

## Dependencies
- flask, flask-cors
- pandas, numpy, scikit-learn, joblib, xgboost
- gunicorn

## Deployment
- Target: autoscale
- Run command: `gunicorn --bind=0.0.0.0:5000 --reuse-port app:app`
