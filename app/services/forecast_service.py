"""Forecast service for predictions."""
import os
import sys
import numpy as np
import xgboost as xgb
import pandas as pd
import pickle
import json
from datetime import datetime, timedelta


# Get backend directory for models and features
BACKEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'backend'
)


class ModelCache:
    """Cache for lazy-loaded ML models."""
    _cache = {}
    
    @classmethod
    def get(cls, key):
        """Get cached model."""
        return cls._cache.get(key)
    
    @classmethod
    def set(cls, key, value):
        """Set cached model."""
        cls._cache[key] = value
    
    @classmethod
    def has(cls, key):
        """Check if model is cached."""
        return key in cls._cache


class ForecastService:
    """Service for weather forecasting."""
    
    @staticmethod
    def _load_pickle_or_joblib(path):
        """Load model from pickle or joblib file."""
        try:
            import joblib
            return joblib.load(path)
        except Exception:
            pass
        
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load model from: {path}. Error: {e}")
    
    @staticmethod
    def _load_xgboost_json(path):
        """Load XGBoost model from JSON file."""
        try:
            if not os.path.exists(path):
                return None
            model = xgb.Booster()
            model.load_model(path)
            return model
        except Exception as e:
            print(f"Failed to load XGBoost model from {path}: {e}")
            return None
    
    @staticmethod
    def _load_json_file(path):
        """Load JSON file (for features)."""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load JSON from {path}: {e}")
            return None
    
    @staticmethod
    def _get_model_for_metric(metric_name, hours):
        """Get model for specific metric and horizon."""
        cache_key = f"model_{metric_name}_{hours}hr"
        
        if not ModelCache.has(cache_key):
            json_path = os.path.join(BACKEND_DIR, f"{metric_name}_{hours}hr.json")
            model = ForecastService._load_xgboost_json(json_path)
            ModelCache.set(cache_key, model)
        
        return ModelCache.get(cache_key)
    
    @classmethod
    def get_temperature_model(cls, hours):
        """Get temperature model for horizon."""
        return cls._get_model_for_metric("Temperature", hours)
    
    @classmethod
    def get_humidity_model(cls, hours):
        """Get humidity model for horizon."""
        return cls._get_model_for_metric("Humidity", hours)
    
    @classmethod
    def get_solar_radiation_model(cls, hours):
        """Get solar radiation model for horizon."""
        return cls._get_model_for_metric("Solar_Radiation", hours)
    
    @classmethod
    def _get_feature_columns(cls):
        """Get feature columns for model."""
        if not ModelCache.has('feature_columns'):
            features = cls._load_json_file(
                os.path.join(BACKEND_DIR, "features.json")
            )
            if features is None:
                features_path = os.path.join(BACKEND_DIR, "feature_columns.pkl")
                if os.path.exists(features_path):
                    try:
                        features = cls._load_pickle_or_joblib(features_path)
                    except Exception:
                        features = None
            ModelCache.set('feature_columns', features)
        
        return ModelCache.get('feature_columns')
    
    @classmethod
    def _prepare_input(cls, data):
        """Prepare input for model prediction."""
        feature_columns = cls._get_feature_columns()
        df = pd.DataFrame([data])
        
        if feature_columns is None:
            return df
        
        if "Hour_sin" in feature_columns and "Hour_sin" not in data:
            hour = data.get("Hour", 0)
            df["Hour_sin"] = np.sin(2 * np.pi * hour / 24)
            df["Hour_cos"] = np.cos(2 * np.pi * hour / 24)
        
        df = df.reindex(columns=feature_columns, fill_value=0)
        return df
    
    @classmethod
    def make_prediction(cls, hours, base_dt, metric=None):
        """Make prediction for given time and metric.
        
        Args:
            hours: Forecast horizon (1, 4, or 24)
            base_dt: Base datetime for prediction
            metric: Optional metric name
            
        Returns:
            Prediction value or None
        """
        feature_columns = cls._get_feature_columns()
        
        if feature_columns is None:
            return None
        
        hour = base_dt.hour
        input_data = {
            "Month": base_dt.month,
            "DayOfYear": base_dt.timetuple().tm_yday,
            "Hour_sin": np.sin(2 * np.pi * hour / 24),
            "Hour_cos": np.cos(2 * np.pi * hour / 24),
        }
        
        df = cls._prepare_input(input_data)
        
        if metric == 'Temperature':
            model = cls.get_temperature_model(hours)
        elif metric == 'Humidity':
            model = cls.get_humidity_model(hours)
        elif metric == 'Solar_Radiation':
            model = cls.get_solar_radiation_model(hours)
        else:
            model = None
        
        if model is None:
            return None
        
        try:
            dmatrix = xgb.DMatrix(df)
            pred = model.predict(dmatrix)
            
            if isinstance(pred, np.ndarray):
                if pred.ndim == 2:
                    pred = pred[0]
                elif pred.ndim == 1 and len(pred) > 1:
                    if metric is not None:
                        pred = pred[0] if len(pred) > 0 else 0
            
            return np.asarray(pred) if not isinstance(pred, (int, float)) else pred
        except Exception as e:
            print(f"Prediction error: {e}")
            try:
                pred = model.predict(df)
                if hasattr(pred, 'shape') and len(pred.shape) > 1:
                    pred = pred[0]
                return np.asarray(pred)
            except Exception as e2:
                print(f"Fallback prediction failed: {e2}")
                return None
    
    @staticmethod
    def _extract_scalar(pred):
        """Extract scalar value from prediction."""
        if pred is None:
            return 0
        if isinstance(pred, (int, float)):
            return float(pred)
        if isinstance(pred, np.ndarray):
            pred = np.asarray(pred).flatten()
            if len(pred) > 0:
                return float(pred[0])
        return 0
    
    @classmethod
    def get_forecast(cls, date_str, time_str, am_pm, hours=1):
        """Get forecast for specific date, time, and horizon.
        
        Args:
            date_str: Date (YYYY-MM-DD)
            time_str: Time (HH:MM)
            am_pm: AM/PM indicator
            hours: Forecast horizon
            
        Returns:
            Dictionary with forecast data or None
        """
        try:
            target_dt = datetime.strptime(
                f"{date_str} {time_str} {am_pm}",
                "%Y-%m-%d %I:%M %p"
            )
            base_dt = target_dt - timedelta(hours=int(hours))
            
            temp_pred = cls.make_prediction(int(hours), base_dt, 
                                           metric='Temperature')
            humidity_pred = cls.make_prediction(int(hours), base_dt, 
                                               metric='Humidity')
            solar_pred = cls.make_prediction(int(hours), base_dt, 
                                            metric='Solar_Radiation')
            
            temperature = cls._extract_scalar(temp_pred)
            humidity = cls._extract_scalar(humidity_pred)
            solar_radiation = cls._extract_scalar(solar_pred)
            
            wind_speed = 0
            wind_direction = 0
            rainfall = 0
            
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
            return None
