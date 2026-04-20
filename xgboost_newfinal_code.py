# -*- coding: utf-8 -*-
"""xgboost_newfinal_code.py
"""

# ============================================
# FAST + IMPROVED PIPELINE (VERSION 2)
# ============================================

import pandas as pd
import numpy as np
import os
import joblib
from datetime import datetime

from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

# ============================================
# CONFIG
# ============================================

DATA_PATH = "updated_sensor_data.csv"

TARGET_COLS = ["Temperature", "Humidity", "Solar_Radiation"]

HORIZONS = {
    "1hr": 60,
    "4hr": 240,
    "24hr": 1440
}

FEATURES = [
    "Month", "DayOfYear",
    "Hour_sin", "Hour_cos",
    "Temp_lag1", "Temp_lag2",
    "Hum_lag1",
    "Solar_lag1", "Solar_lag2"
]

# Ensure dirs exist
os.makedirs("models", exist_ok=True)
os.makedirs("results", exist_ok=True)

models = {}

def train_models_if_needed():
    global models
    if len(models) == len(HORIZONS):
        return  # Already loaded

    missing_models = not all(os.path.exists(f"models/model_{hz}_v2.pkl") for hz in HORIZONS.keys())
    
    if missing_models:
        print("Models not found or incomplete. Starting training process...")
        train()
        
    # Load models safely
    print("Loading models into memory...")
    models = {
        "1hr": joblib.load("models/model_1hr_v2.pkl"),
        "4hr": joblib.load("models/model_4hr_v2.pkl"),
        "24hr": joblib.load("models/model_24hr_v2.pkl")
    }
    print("Models loaded successfully.")

def get_model():
    return MultiOutputRegressor(
        XGBRegressor(
            n_estimators=80,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            tree_method="hist",
            random_state=42
        )
    )

def train():
    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip()

    col_map = {}
    for col in df.columns:
        c = col.lower()
        if "temp" in c:
            col_map[col] = "Temperature"
        elif "hum" in c or "rh" in c:
            col_map[col] = "Humidity"
        elif "solar" in c or "radiation" in c:
            col_map[col] = "Solar_Radiation"
        elif "date" in c or "time" in c:
            col_map[col] = "Date and Time"

    df.rename(columns=col_map, inplace=True)
    df["Timestamp"] = pd.to_datetime(df["Date and Time"], dayfirst=True)
    df = df.sort_values("Timestamp")
    df["Month"] = df["Timestamp"].dt.month
    df["DayOfYear"] = df["Timestamp"].dt.dayofyear
    df["Hour"] = df["Timestamp"].dt.hour
    df["Hour_sin"] = np.sin(2 * np.pi * df["Hour"] / 24)
    df["Hour_cos"] = np.cos(2 * np.pi * df["Hour"] / 24)
    df["Solar_Radiation"] = df["Solar_Radiation"].clip(lower=0)
    df["Temp_lag1"] = df["Temperature"].shift(1)
    df["Temp_lag2"] = df["Temperature"].shift(2)
    df["Hum_lag1"] = df["Humidity"].shift(1)
    df["Solar_lag1"] = df["Solar_Radiation"].shift(1)
    df["Solar_lag2"] = df["Solar_Radiation"].shift(2)
    df.dropna(inplace=True)
    df = df.tail(15000)

    print("✅ Data Ready:", df.shape)
    all_results = []

    for name, shift in HORIZONS.items():
        print(f"\n🚀 Training {name}")
        df_future = df.copy()
        for col in TARGET_COLS:
            df_future[col] = df_future[col].shift(-shift)
        df_future.dropna(inplace=True)

        X = df_future[FEATURES]
        y = df_future[TARGET_COLS]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = get_model()
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        print("\n📊 Metrics:")
        for i, col in enumerate(TARGET_COLS):
            mae = mean_absolute_error(y_test[col], y_pred[:, i])
            rmse = np.sqrt(mean_squared_error(y_test[col], y_pred[:, i]))
            r2 = r2_score(y_test[col], y_pred[:, i])
            acc = max(0, r2) * 100
            print(f"{col}: MAE={mae:.3f}, RMSE={rmse:.3f}, R2={r2:.3f}, Acc={acc:.2f}%")
            all_results.append({
                "Horizon": name,
                "Parameter": col,
                "MAE": mae,
                "RMSE": rmse,
                "R2": r2,
                "Accuracy(%)": acc
            })

        model_path = f"models/model_{name}_v2.pkl"
        joblib.dump(model, model_path)
        print(f"✅ Model Saved: {model_path}")

        df_out = y_test.reset_index(drop=True)
        for i, col in enumerate(TARGET_COLS):
            df_out[f"{col}_Pred"] = y_pred[:, i]
        df_out["Solar_Radiation_Pred"] = df_out["Solar_Radiation_Pred"].clip(lower=0)

        pred_path = f"results/actual_vs_predicted_{name}_v2.csv"
        df_out.to_csv(pred_path, index=False)
        print(f"✅ Predictions Saved: {pred_path}")

    metrics_path = "results/metrics_v2.csv"
    pd.DataFrame(all_results).to_csv(metrics_path, index=False)
    print("\n🎉 ALL DONE!")

# ============================================
# CONSTANTS
# ============================================
rho = 1.225
A = 0.045
eta = 0.45
Ac = 1.62
Cp = 1005
velocities = [0.25, 0.5, 0.75, 1, 1.25, 1.5]

PRODUCT_MULTIPLIERS = {
    'carrot': 0.6,
    'chilli': 0.8,
    'grain': 1.2,
    'mango': 1.0,
    'fish': 0.4,
    'tomato': 0.7,
    'ginger': 1.4,
    'other': 1.0
}

cached_lags = None
df_history = None

def init_history():
    global df_history
    if df_history is not None:
        return
    try:
        print("Pre-loading historical sensor data from CSV into memory...")
        df = pd.read_csv(DATA_PATH)
        df.columns = df.columns.str.strip()
        temp_col = [c for c in df.columns if "temp" in c.lower()][0]
        hum_col = [c for c in df.columns if "hum" in c.lower() or "rh" in c.lower()][0]
        solar_col = [c for c in df.columns if "solar" in c.lower() or "radiation" in c.lower()][0]
        date_col = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()][0]
        
        df = df[[date_col, temp_col, hum_col, solar_col]].copy()
        df.rename(columns={
            date_col: "Timestamp",
            temp_col: "Temperature",
            hum_col: "Humidity",
            solar_col: "Solar"
        }, inplace=True)
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], dayfirst=True)
        df = df.sort_values("Timestamp")
        df_history = df.tail(15000)
        print("Live logs cached successfully!")
    except Exception as e:
        print("Failed to load live lags, using default values. Error:", e)

def get_live_lags():
    global cached_lags
    init_history()
    
    if df_history is not None and not df_history.empty:
        last_rows = df_history.tail(3)
        temps = last_rows["Temperature"].values
        hums = last_rows["Humidity"].values
        solars = last_rows["Solar"].values

        cached_lags = {
            "Temp_lag1": temps[-2] if len(temps) >= 2 else temps[-1],
            "Temp_lag2": temps[-3] if len(temps) >= 3 else temps[-1],
            "Hum_lag1": hums[-2] if len(hums) >= 2 else hums[-1],
            "Solar_lag1": solars[-2] if len(solars) >= 2 else solars[-1],
            "Solar_lag2": solars[-3] if len(solars) >= 3 else solars[-1],
        }
    else:
        cached_lags = {
            "Temp_lag1": 30, "Temp_lag2": 30,
            "Hum_lag1": 60,
            "Solar_lag1": 200, "Solar_lag2": 200
        }
    return cached_lags

def get_historical_lags(dt):
    init_history()
    
    if df_history is not None and not df_history.empty:
        # Strictly get all rows chronologically PRIOR to this target prediction timestamp
        past_df = df_history[df_history["Timestamp"] < pd.to_datetime(dt)]
        
        if not past_df.empty:
            last_rows = past_df.tail(3)
            temps = last_rows["Temperature"].values
            hums = last_rows["Humidity"].values
            solars = last_rows["Solar"].values

            return {
                "Temp_lag1": temps[-2] if len(temps) >= 2 else temps[-1],
                "Temp_lag2": temps[-3] if len(temps) >= 3 else temps[-1],
                "Hum_lag1": hums[-2] if len(hums) >= 2 else hums[-1],
                "Solar_lag1": solars[-2] if len(solars) >= 2 else solars[-1],
                "Solar_lag2": solars[-3] if len(solars) >= 3 else solars[-1],
            }
            
    # Fallback if predicting deeply in unrecorded future or no datalog
    return get_live_lags()

def get_live_data():
    init_history()
    if df_history is None or df_history.empty:
        return {"temperature": 0, "humidity": 0, "solar_radiation": 0, "wind_speed": 0, "rainfall": 0, "wind_direction": 0}
    
    last_row = df_history.iloc[-1]
    return {
        "temperature": float(last_row["Temperature"]),
        "humidity": float(last_row["Humidity"]),
        "solar_radiation": float(last_row["Solar"]),
        "wind_speed": 1.5,
        "rainfall": 0.0,
        "wind_direction": 180
    }

def get_historical_data(interval=60):
    init_history()
    if df_history is None or df_history.empty:
        return {"timestamps": [], "data": {}}
    
    step = max(1, int(interval))
    sampled = df_history.iloc[::-step][::-1].tail(20) # Get last 20 sparse points 
    
    return {
        "timestamps": sampled["Timestamp"].dt.strftime("%Y-%m-%d %H:%M").tolist(),
        "data": {
            "temperature": sampled["Temperature"].tolist(),
            "humidity": sampled["Humidity"].tolist(),
            "solar": sampled["Solar"].tolist(),
            "wind": [1.5]*len(sampled),
            "rainfall": [0.0]*len(sampled),
            "wind_direction": [180]*len(sampled),
        }
    }

def get_raw_prediction(user_datetime, horizon=1):
    train_models_if_needed()
    dt = datetime.strptime(user_datetime, "%Y-%m-%d %H:%M:%S")
    
    h_str = str(horizon)
    if h_str == "24":
        model = models["24hr"]
    elif h_str == "4":
        model = models["4hr"]
    else:
        model = models["1hr"]
        
    X = create_input(dt)
    pred = model.predict(X)[0]
    return {
        "temperature": round(float(pred[0]), 2),
        "humidity": round(float(pred[1]), 2),
        "solar_radiation": round(float(pred[2]), 2),
        "wind_speed": 1.5,
        "rainfall": 0.0,
        "wind_direction": 185
    }

def select_model(user_datetime):
    now = datetime.now()
    target = datetime.strptime(user_datetime, "%Y-%m-%d %H:%M:%S")

    diff = (target - now).total_seconds() / 3600
    if diff <= 2:
        return models["1hr"]
    elif diff <= 6:
        return models["4hr"]
    else:
        return models["24hr"]

def create_input(dt):
    lags = get_historical_lags(dt)
    return pd.DataFrame([{
        "Month": dt.month,
        "DayOfYear": dt.timetuple().tm_yday,
        "Hour_sin": np.sin(2 * np.pi * dt.hour / 24),
        "Hour_cos": np.cos(2 * np.pi * dt.hour / 24),
        "Temp_lag1": lags["Temp_lag1"],
        "Temp_lag2": lags["Temp_lag2"],
        "Hum_lag1": lags["Hum_lag1"],
        "Solar_lag1": lags["Solar_lag1"],
        "Solar_lag2": lags["Solar_lag2"]
    }])

def get_solar(hour):
    if 6 <= hour <= 18:
        return 400 * np.sin(np.pi * (hour - 6) / 12)
    return 0

def get_drying_time(user_datetime, thickness, user_temp=40, product='other'):
    train_models_if_needed()
    if not (2 <= thickness <= 8):
        return None
    dt = datetime.strptime(user_datetime, "%Y-%m-%d %H:%M:%S")
    model = select_model(user_datetime)
    X = create_input(dt)
    pred = model.predict(X)[0]
    Ti = pred[0]
    
    # Factor in user's supplemental heater setting from frontend UI
    if user_temp > Ti:
        Ti = user_temp
        
    Gt = get_solar(dt.hour)

    best_time = float('inf')
    for v in velocities:
        m_dot = rho * A * v
        if Gt > 0:
            To = Ti + (eta * Ac * Gt) / (m_dot * Cp)
        else:
            To = Ti # Night time or no solar radiation means we rely entirely on Ti (ambient/heater)
            
        drying_time = (
            1239
            + 55.3 * thickness
            - 35.17 * To
            + 5.23 * thickness**2
            + 0.3031 * To**2
            - 1.357 * thickness * To
        )
        best_time = min(best_time, drying_time)
        
    # Scale based on product type to guarantee more accurate predictions based on moisture variance
    multiplier = PRODUCT_MULTIPLIERS.get(product.lower(), 1.0)
    best_time *= multiplier
    
    # Convert from minutes to hours for the frontend
    best_time /= 60
    
    return round(best_time, 2)

if __name__ == "__main__":
    train_models_if_needed()
    print("10 AM:", get_drying_time("2026-04-01 10:00:00", 4, 35, 'fish'))