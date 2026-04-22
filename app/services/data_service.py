"""Data service for dashboard and data retrieval."""
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.utils import validate_interval


# Get backend directory
BACKEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'backend'
)
DATA_PATH = os.path.join(BACKEND_DIR, 'data', 'drying_forecast_data.csv')
APRIL_FORECAST_PATH = os.path.join(BACKEND_DIR, 'data', 'april_forecast_2026.csv')


class DataService:
    """Service for managing weather and dashboard data."""
    
    _df = None
    _april_df = None
    
    @classmethod
    def _load_main_data(cls):
        """Lazy load main forecast data."""
        if cls._df is None:
            try:
                cls._df = pd.read_csv(DATA_PATH)
                cls._df.columns = [c.strip() for c in cls._df.columns]
                if 'Timestamp' not in cls._df.columns:
                    raise ValueError("CSV missing 'Timestamp' column")
            except Exception as e:
                print(f"Error loading main data: {e}")
                cls._df = pd.DataFrame(
                    columns=["Timestamp", "Temperature", "Humidity", 
                            "Rainfall", "Wind", "Solar"]
                )
        return cls._df
    
    @classmethod
    def _load_april_data(cls):
        """Lazy load April forecast data."""
        if cls._april_df is None:
            try:
                if os.path.exists(APRIL_FORECAST_PATH):
                    cls._april_df = pd.read_csv(APRIL_FORECAST_PATH)
                else:
                    cls._april_df = pd.DataFrame()
            except Exception as e:
                print(f"Error loading April data: {e}")
                cls._april_df = pd.DataFrame()
        return cls._april_df
    
    @staticmethod
    def get_current_time_str():
        """Get current time as HH:MM string."""
        return datetime.now().strftime("%H:%M")
    
    @classmethod
    def get_live_readings(cls):
        """Get current live sensor readings.
        
        Returns:
            Dictionary with current sensor values
        """
        df = cls._load_main_data()
        now_str = cls.get_current_time_str()
        row = df[df['Timestamp'] == now_str]
        
        if row.empty:
            if not df.empty:
                row = df.iloc[[-1]]
            else:
                return {
                    "temperature": 0,
                    "humidity": 0,
                    "rainfall": 0,
                    "wind_speed": 0,
                    "solar_radiation": 0,
                    "wind_direction": 0,
                    "time": now_str
                }
        
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
    
    @classmethod
    def get_dashboard_data(cls, minutes=60):
        """Get dashboard data for specified interval.
        
        Args:
            minutes: Interval in minutes
            
        Returns:
            Tuple of (timestamps, data_dict)
        """
        df = cls._load_main_data()
        
        try:
            if df.empty:
                return [], {}
            
            minutes_needed = validate_interval(minutes)
            current_time = cls.get_current_time_str()
            now_matches = df[df['Timestamp'] == current_time]
            
            if not now_matches.empty:
                start_idx = now_matches.index[0]
            else:
                start_idx = max(0, len(df) - 1)
            
            end_idx = start_idx + minutes_needed
            
            if end_idx < len(df):
                subset = df.iloc[start_idx:end_idx]
            else:
                remaining = end_idx - len(df)
                subset = pd.concat([df.iloc[start_idx:], df.iloc[:remaining]])
            
            # Smart downsampling
            step = 1
            if minutes_needed > 1440:
                step = 30
            elif minutes_needed > 480:
                step = 10
            elif minutes_needed > 240:
                step = 5
            elif minutes_needed > 120:
                step = 2
            
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
            return [], {}
    
    @classmethod
    def get_dashboard_data_range(cls, start_date_str, end_date_str, interval=60):
        """Get dashboard data for date range.
        
        Args:
            start_date_str: Start date (YYYY-MM-DD)
            end_date_str: End date (YYYY-MM-DD)
            interval: Interval in minutes
            
        Returns:
            Tuple of (timestamps, data_dict)
        """
        df = cls._load_main_data()
        
        try:
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
            
            # Limit to max 7 days
            delta = end_dt - start_dt
            if delta.days > 7:
                end_dt = start_dt + timedelta(days=7)
            
            # Load April data if needed
            april_df = cls._load_april_data()
            april_data_dict = {}
            
            if not april_df.empty:
                for _, row in april_df.iterrows():
                    dt_key = str(row['DateTime']).strip()
                    april_data_dict[dt_key] = row
            
            interval = validate_interval(interval)
            start_month = start_dt.month
            is_april = (start_month == 4)
            use_april_data = is_april and interval >= 60
            
            step_minutes = interval if interval < 60 else max(1, interval)
            
            timestamps = []
            temps, hums, rains, winds, solars, dirs = [], [], [], [], [], []
            
            current = start_dt
            
            while current <= end_dt + timedelta(hours=23, minutes=59):
                if step_minutes >= 60:
                    rounded_current = current.replace(minute=0, second=0, microsecond=0)
                else:
                    rounded_current = current.replace(second=0, microsecond=0)
                
                dt_str = rounded_current.strftime("%Y-%m-%d %H:%M")
                data_found = False
                
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
                            data_found = True
                        except Exception as e:
                            print(f"Error processing April row: {e}")
                
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
                            data_found = True
                        except Exception as e:
                            print(f"Error processing fallback row: {e}")
                
                current += timedelta(minutes=step_minutes)
            
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
            print(f"Error in get_dashboard_data_range: {e}")
            return [], {}
