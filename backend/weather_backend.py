import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import pickle
import json
import xgboost as xgb

# Used for absolute paths so Flask working directory does not break loading.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = BASE_DIR

# Cache for lazy-loaded models (avoid reloading)
_model_cache = {}


def _load_pickle_or_joblib(path: str):
    """Best-effort loader for models/features saved via pickle/joblib.

    Note: joblib sometimes stores objects in a way that plain `pickle.load()`
    can deserialize into an incorrect intermediate type. Prefer joblib first.
    """
    # Prefer joblib for models dumped with `joblib.dump`.
    try:
        import joblib  # imported lazily

        return joblib.load(path)
    except Exception:
        pass

    # Fallback to pickle for legacy artifacts.
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load model/features from: {path}. Error: {e}")


def _load_first_existing(candidates):
    for rel_name in candidates:
        p = os.path.join(MODEL_DIR, rel_name)
        if os.path.exists(p):
            try:
                return _load_pickle_or_joblib(p)
            except Exception as e:
                # If a file is corrupted/misplaced, don't crash the whole Flask app.
                print(f"Warning: failed to load '{rel_name}' from '{MODEL_DIR}': {e}")
                continue
    return None


def _load_xgboost_json(path: str):
    """Load an XGBoost model from a JSON file."""
    try:
        model = xgb.Booster()
        model.load_model(path)
        print(f"✅ Successfully loaded XGBoost model from {path}")
        return model
    except Exception as e:
        print(f"❌ Failed to load XGBoost model from {path}: {e}")
        return None


def _load_json_file(path: str):
    """Load a JSON file (for features, etc.)."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: failed to load JSON from {path}: {e}")
        return None


# =========================
# LAZY MODEL LOADING - Individual Metrics
# =========================
# Models are stored per metric and horizon

def _get_model_for_metric(metric_name, hours):
    """Load a model for a specific metric and horizon."""
    cache_key = f"model_{metric_name}_{hours}hr"
    
    if cache_key not in _model_cache:
        json_path = os.path.join(MODEL_DIR, f"{metric_name}_{hours}hr.json")
        model = _load_xgboost_json(json_path)
        _model_cache[cache_key] = model
    
    return _model_cache[cache_key]

def get_temperature_model(hours):
    return _get_model_for_metric("Temperature", hours)

def get_humidity_model(hours):
    return _get_model_for_metric("Humidity", hours)

def get_solar_radiation_model(hours):
    return _get_model_for_metric("Solar_Radiation", hours)

def get_model_1hr():
    if 'model_1hr' not in _model_cache:
        # Try XGBoost JSON first (multi-output), then fallback to pickle
        model = _load_xgboost_json(os.path.join(MODEL_DIR, "Temperature_1hr.json"))
        if model is None:
            model = _load_first_existing(["forecast_model_1hr.pkl"])
        _model_cache['model_1hr'] = model
    return _model_cache['model_1hr']

def get_model_4hr():
    if 'model_4hr' not in _model_cache:
        # Try XGBoost JSON first, then fallback to pickle
        model = _load_xgboost_json(os.path.join(MODEL_DIR, "Temperature_4hr.json"))
        if model is None:
            model = _load_first_existing(["forecast_model_4hr.pkl", "forecast_model_4hr (4).pkl"])
        _model_cache['model_4hr'] = model
    return _model_cache['model_4hr']

def get_model_24hr():
    if 'model_24hr' not in _model_cache:
        # Try XGBoost JSON first, then fallback to pickle
        model = _load_xgboost_json(os.path.join(MODEL_DIR, "Temperature_24hr.json"))
        if model is None:
            model = _load_first_existing(["forecast_model_24hr.pkl", "forcast_model_24hr.pkl"])
        _model_cache['model_24hr'] = model
    return _model_cache['model_24hr']

def get_feature_columns():
    if 'feature_columns' not in _model_cache:
        # Try features.json first, then fallback to pickle
        features = _load_json_file(os.path.join(MODEL_DIR, "features.json"))
        if features is None:
            features = _load_first_existing(["feature_columns.pkl"])
        _model_cache['feature_columns'] = features
    return _model_cache['feature_columns']


# =========================
# MODEL HELPERS
# =========================
def select_model(hours):
    if hours == 1:
        return get_model_1hr()
    elif hours == 4:
        return get_model_4hr()
    elif hours == 24:
        return get_model_24hr()
    return None


def prepare_input(data):
    """Prepare input for model prediction with proper feature engineering."""
    feature_columns = get_feature_columns()
    
    # Create base dictionary with provided data
    df = pd.DataFrame([data])
    
    if feature_columns is None:
        return df
    
    # For XGBoost models, we need to ensure all expected features are present
    # Apply feature engineering if needed
    if "Hour_sin" in feature_columns and "Hour_sin" not in data:
        hour = data.get("Hour", 0)
        df["Hour_sin"] = np.sin(2 * np.pi * hour / 24)
        df["Hour_cos"] = np.cos(2 * np.pi * hour / 24)
    
    # Reindex to match feature column order
    df = df.reindex(columns=feature_columns, fill_value=0)
    return df


def make_prediction(hours, base_dt: datetime, metric=None):
    """Make a prediction using the appropriate model.
    
    Args:
        hours: Forecast horizon (1, 4, or 24)
        base_dt: Base datetime for prediction
        metric: Optional metric name ('Temperature', 'Humidity', 'Solar_Radiation')
                If None, returns from the general model
    """
    feature_columns = get_feature_columns()
    
    if feature_columns is None:
        return None

    # Prepare features: Month, DayOfYear, Hour_sin, Hour_cos
    hour = base_dt.hour
    input_data = {
        "Month": base_dt.month,
        "DayOfYear": base_dt.timetuple().tm_yday,
        "Hour_sin": np.sin(2 * np.pi * hour / 24),
        "Hour_cos": np.cos(2 * np.pi * hour / 24),
    }
    
    df = prepare_input(input_data)
    
    # Select model based on metric or general model
    if metric == 'Temperature':
        model = get_temperature_model(hours)
    elif metric == 'Humidity':
        model = get_humidity_model(hours)
    elif metric == 'Solar_Radiation':
        model = get_solar_radiation_model(hours)
    else:
        model = select_model(hours)
    
    if model is None:
        return None
    
    try:
        # For XGBoost models, use the DMatrix interface
        dmatrix = xgb.DMatrix(df)
        pred = model.predict(dmatrix)
        
        # Handle both single output and multi-output models
        if isinstance(pred, np.ndarray):
            if pred.ndim == 2:
                pred = pred[0]
            elif pred.ndim == 1 and len(pred) > 1:
                # Already formatted correctly, but for single-metric models return scalar
                if metric is not None:
                    pred = pred[0] if len(pred) > 0 else 0
        
        return np.asarray(pred) if not isinstance(pred, (int, float)) else pred
    except Exception as e:
        print(f"Prediction error with XGBoost (trying standard predict): {e}")
        try:
            # Fallback for non-XGBoost models
            pred = model.predict(df)
            if hasattr(pred, 'shape') and len(pred.shape) > 1:
                pred = pred[0]
            return np.asarray(pred)
        except Exception as e2:
            print(f"Prediction fallback also failed: {e2}")
            return None


# =========================
# LOAD DATA
# =========================
DATA_PATH = os.path.join(BASE_DIR, 'data', 'drying_forecast_data.csv')

try:
    df = pd.read_csv(DATA_PATH)
    df.columns = [c.strip() for c in df.columns]

    if 'Timestamp' not in df.columns:
        raise ValueError("CSV missing 'Timestamp' column")

except Exception as e:
    print(f"Error loading data: {e}")
    df = pd.DataFrame(columns=["Timestamp", "Temperature", "Humidity", "Rainfall", "Wind", "Solar"])


# =========================
# LIVE DATA
# =========================
def get_current_time_str():
    return datetime.now().strftime("%H:%M")


def get_live_readings():
    now_str = get_current_time_str()
    row = df[df['Timestamp'] == now_str]

    if row.empty:
        if not df.empty:
            row = df.iloc[[-1]]
        else:
            return {k: 0 for k in ["temperature", "humidity", "rainfall", "wind_speed", "solar_radiation"]}

    data = row.iloc[0].to_dict()

    return {
        "temperature": round(data.get("Temperature", 0), 2),
        "humidity": round(data.get("Humidity", 0), 2),
        "rainfall": round(data.get("Rainfall", 0), 2),
        "wind_speed": round(data.get("Wind", 0), 2),
        "solar_radiation": round(data.get("Solar", 0), 2),
        "wind_direction": np.random.randint(0, 360),
        "time": now_str
    }


# =========================
# DASHBOARD
# =========================
def get_dashboard_data(minutes=60):
    """
    Get dashboard data for the specified interval.
    For small intervals (1-60 min), returns all available data points.
    For larger intervals (>60 min), intelligently downsamples to keep ~30-60 visible points.
    """
    try:
        if df.empty:
            return [], {}
        
        minutes_needed = int(minutes)
        
        # Find the closest matching current time in the data
        # (handles case where exact time isn't available)
        current_time = get_current_time_str()
        now_matches = df[df['Timestamp'] == current_time]
        
        if not now_matches.empty:
            start_idx = now_matches.index[0]
        else:
            # If exact time not found, use the last available data point
            # This ensures we get recent data, not data from beginning of day
            start_idx = max(0, len(df) - 1)
        
        # Calculate end index
        end_idx = start_idx + minutes_needed
        
        # Handle wraparound for circular buffer
        if end_idx < len(df):
            subset = df.iloc[start_idx:end_idx]
        else:
            remaining = end_idx - len(df)
            subset = pd.concat([df.iloc[start_idx:], df.iloc[:remaining]])
        
        # Smart downsampling based on interval size
        # Goal: show between 1 and 60 data points for good visualization
        step = 1
        
        if minutes_needed > 1440:  # More than 24 hours
            step = 30  # Show 1 point every 30 minutes
        elif minutes_needed > 480:  # 8+ hours
            step = 10  # Show 1 point every 10 minutes
        elif minutes_needed > 240:  # 4+ hours
            step = 5   # Show 1 point every 5 minutes
        elif minutes_needed > 120:  # 2+ hours
            step = 2   # Show 1 point every 2 minutes
        # For intervals <= 120 minutes, show all points
        
        subset = subset.iloc[::step]
        
        return (
            subset['Timestamp'].tolist(),
            {
                "temperature": subset['Temperature'].tolist(),
                "humidity": subset['Humidity'].tolist(),
                "rainfall": subset['Rainfall'].tolist(),
                "wind": subset['Wind'].tolist(),
                "solar": subset['Solar'].tolist(),
                "wind_direction": np.random.randint(0, 360, size=len(subset)).tolist()
            }
        )

    except Exception as e:
        print(f"Error in get_dashboard_data: {e}")
        import traceback
        traceback.print_exc()
        return [], {}


# =========================
# 🔥 UPDATED FORECAST (MODEL USED HERE)
# =========================
def get_forecast(date_str, time_str, am_pm, hours=1):
    """Get forecast for a specific date, time, and horizon."""
    try:
        # `date_str + time_str + am_pm` represents the timestamp the user selected.
        # The horizon model predicts target variables at (base_time + horizon).
        # So to predict the selected timestamp, we feed (selected_time - horizon) into the model.
        target_dt = datetime.strptime(
            f"{date_str} {time_str} {am_pm}",
            "%Y-%m-%d %I:%M %p"
        )
        base_dt = target_dt - timedelta(hours=int(hours))

        # Get individual metric predictions
        temp_pred = make_prediction(int(hours), base_dt, metric='Temperature')
        humidity_pred = make_prediction(int(hours), base_dt, metric='Humidity')
        solar_pred = make_prediction(int(hours), base_dt, metric='Solar_Radiation')
        
        # Extract scalar values from predictions
        def extract_scalar(pred):
            """Extract a scalar value from prediction, handling various formats."""
            if pred is None:
                return 0
            if isinstance(pred, (int, float)):
                return float(pred)
            if isinstance(pred, np.ndarray):
                pred = np.asarray(pred).flatten()
                if len(pred) > 0:
                    return float(pred[0])
            return 0
        
        temperature = extract_scalar(temp_pred)
        humidity = extract_scalar(humidity_pred)
        solar_radiation = extract_scalar(solar_pred)
        
        # For wind data, we don't have individual models, use default values
        wind_speed = 0
        wind_direction = 0
        rainfall = 0
        
        # Try to get wind data from the general model (if it exists)
        try:
            general_pred = make_prediction(int(hours), base_dt, metric=None)
            if general_pred is not None:
                general_pred = np.asarray(general_pred).flatten()
                # Expected output order: [Temperature, Humidity, Wind_Speed, WindDir_sin, WindDir_cos, Rainfall, Solar_Radiation]
                if len(general_pred) >= 7:
                    # Use general model predictions if available
                    temperature = float(general_pred[0])
                    humidity = float(general_pred[1])
                    wind_speed = float(general_pred[2])
                    wind_dir_sin = float(general_pred[3])
                    wind_dir_cos = float(general_pred[4])
                    rainfall = float(general_pred[5])
                    solar_radiation = float(general_pred[6])
                    
                    # Convert wind direction from sin/cos to degrees
                    wind_dir_rad = np.arctan2(wind_dir_sin, wind_dir_cos)
                    wind_dir_deg = (np.degrees(wind_dir_rad) + 360.0) % 360.0
                    wind_direction = int(round(wind_dir_deg)) % 360
        except Exception as e:
            print(f"Note: General model not available: {e}")

        return {
            "temperature": round(temperature, 2),
            "solar_radiation": round(solar_radiation, 2),
            "rainfall": round(rainfall, 2),
            "wind_speed": round(wind_speed, 2),
            "humidity": round(humidity, 2),
            "wind_direction": wind_direction,
        }

    except Exception as e:
        print(f"Forecast Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_dashboard_data_range(start_date_str, end_date_str, interval=60):
    """Get data for a date range, using April forecasts when available"""
    try:
        import sys
        
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")

        # Limit to max 7 days
        delta = end_dt - start_dt
        if delta.days > 7:
            end_dt = start_dt + timedelta(days=7)

        print(f"\n🔄 Date range request: {start_date_str} to {end_date_str}", file=sys.stderr)
        sys.stderr.flush()
        
        # Load April forecast data as strings for simple matching
        april_forecast_path = os.path.join(BASE_DIR, 'data', 'april_forecast_2026.csv')
        april_data_dict = {}  # Store as dict with datetime string as key
        april_df = None
        
        if os.path.exists(april_forecast_path):
            try:
                april_df = pd.read_csv(april_forecast_path)
                print(f"✅ Loaded April CSV: {len(april_df)} rows from {april_forecast_path}", file=sys.stderr)
                
                # Create a lookup dict with string keys for fast matching
                for _, row in april_df.iterrows():
                    dt_key = str(row['DateTime']).strip()  # "2026-04-20 00:00", etc
                    april_data_dict[dt_key] = row
                
                print(f"✅ April data dict created with {len(april_data_dict)} entries", file=sys.stderr)
                print(f"   Sample keys: {list(april_data_dict.keys())[:3]}", file=sys.stderr)
                sys.stderr.flush()
            except Exception as e:
                print(f"❌ Error loading April data: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()

        # Normalize interval - support all intervals (1, 5, 10, 60, etc)
        interval = int(interval)
        
        # Decision logic: which data source to use based on interval
        # - For intervals < 60 minutes: use fallback data (has minute-level granularity)
        # - For intervals >= 60 minutes: use April data if available (hourly granularity is fine)
        start_month = start_dt.month
        end_month = end_dt.month
        is_april = (start_month == 4 or end_month == 4)
        use_april_data = is_april and interval >= 60
        
        # Set step size based on interval
        step_minutes = interval if interval < 60 else max(1, interval)
        
        print(f"   Interval: {interval}min, Step: {step_minutes}min, Using April: {use_april_data}", file=sys.stderr)
        sys.stderr.flush()

        timestamps = []
        temps, hums, rains, winds, solars, dirs = [], [], [], [], [], []

        current = start_dt
        data_points_from_april = 0
        data_points_from_fallback = 0
        
        while current <= end_dt + timedelta(hours=23, minutes=59):
            # Format timestamp - for small intervals keep exact minute, for large intervals round to hour
            if step_minutes >= 60:
                rounded_current = current.replace(minute=0, second=0, microsecond=0)
            else:
                # For small intervals, use exact time (already incremented by step_minutes)
                rounded_current = current.replace(second=0, microsecond=0)
            
            dt_str = rounded_current.strftime("%Y-%m-%d %H:%M")
            
            data_found = False
            
            # For April dates with larger intervals (>=60min), try April forecast data first
            if use_april_data:
                lookup_current = current.replace(minute=0, second=0, microsecond=0)
                lookup_dt_str = lookup_current.strftime("%Y-%m-%d %H:%M")
                
                if april_data_dict and lookup_dt_str in april_data_dict:
                    try:
                        row = april_data_dict[lookup_dt_str]
                        timestamps.append(dt_str)
                        temps.append(float(row['Temperature']))
                        hums.append(float(row['Humidity']))
                        rains.append(float(row['Rainfall']))
                        winds.append(float(row['Wind']))
                        solars.append(float(row['Solar']))
                        dirs.append(np.random.randint(0, 360))
                        data_points_from_april += 1
                        data_found = True
                    except Exception as e:
                        print(f"⚠️ Error processing April row for {lookup_dt_str}: {e}", file=sys.stderr)

            # Fallback: Use time-only matching from drying data
            # This works for all months and smaller intervals
            if not data_found:
                time_key = rounded_current.strftime("%H:%M")
                fallback_rows = df[df['Timestamp'] == time_key]
                
                if not fallback_rows.empty:
                    try:
                        d = fallback_rows.iloc[0]
                        timestamps.append(dt_str)
                        temps.append(float(d['Temperature']))
                        hums.append(float(d['Humidity']))
                        rains.append(float(d['Rainfall']))
                        winds.append(float(d['Wind']))
                        solars.append(float(d['Solar']))
                        dirs.append(np.random.randint(0, 360))
                        data_points_from_fallback += 1
                        data_found = True
                    except Exception as e:
                        print(f"⚠️ Error processing fallback row for {time_key}: {e}", file=sys.stderr)

            if not data_found:
                print(f"⚠️ No data found for {dt_str}", file=sys.stderr)

            current += timedelta(minutes=step_minutes)

        print(f"\n📊 Date range complete:", file=sys.stderr)
        print(f"   Total points: {len(timestamps)}", file=sys.stderr)
        print(f"   From April forecast: {data_points_from_april}", file=sys.stderr)
        print(f"   From fallback: {data_points_from_fallback}", file=sys.stderr)
        sys.stderr.flush()
        
        return (
            timestamps,
            {
                "temperature": temps,
                "humidity": hums,
                "rainfall": rains,
                "wind": winds,
                "solar": solars,
                "wind_direction": dirs
            }
        )

    except Exception as e:
        import traceback
        print(f"❌ RANGE ERROR: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        
        # Also print to stdout for better visibility
        error_msg = traceback.format_exc()
        print(f"\n❌ RANGE ERROR (VISIBLE): {e}")
        print(error_msg)
        
        return [], {}
  