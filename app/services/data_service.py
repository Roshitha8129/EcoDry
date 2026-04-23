"""Data service for dashboard and data retrieval.

Single source of truth: backend/updated_sensor_data.csv

Expected columns (from the sensor):
    S.No., Date and Time, Temperature, RH, Solar Radiation

Mapping used internally:
    Date and Time   -> DateTime (parsed) + Timestamp (HH:MM)
    Temperature     -> Temperature
    RH              -> Humidity
    Solar Radiation -> Solar
    (no sensor)     -> Rainfall = 0
    (no sensor)     -> Wind     = 0
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.utils import validate_interval


BACKEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'backend'
)
DATA_PATH = os.path.join(BACKEND_DIR, 'updated_sensor_data.csv')


class DataService:
    """Service for managing weather and dashboard data."""

    _df = None

    @classmethod
    def _load_main_data(cls):
        """Lazy-load and normalise the sensor data."""
        if cls._df is not None:
            return cls._df

        try:
            df = pd.read_csv(DATA_PATH)
            df.columns = [c.strip() for c in df.columns]

            if 'Date and Time' not in df.columns:
                raise ValueError("CSV missing 'Date and Time' column")

            # Parse the full datetime (sensor format: DD-MM-YYYY HH:MM)
            df['DateTime'] = pd.to_datetime(
                df['Date and Time'], format='%d-%m-%Y %H:%M', errors='coerce'
            )
            df = df.dropna(subset=['DateTime']).reset_index(drop=True)

            # Build a HH:MM string column for time-based lookups
            df['Timestamp'] = df['DateTime'].dt.strftime('%H:%M')

            # Standardise metric column names
            if 'RH' in df.columns:
                df['Humidity'] = pd.to_numeric(df['RH'], errors='coerce').fillna(0)
            else:
                df['Humidity'] = 0.0

            if 'Solar Radiation' in df.columns:
                df['Solar'] = pd.to_numeric(
                    df['Solar Radiation'], errors='coerce'
                ).fillna(0)
            else:
                df['Solar'] = 0.0

            df['Temperature'] = pd.to_numeric(
                df.get('Temperature', 0), errors='coerce'
            ).fillna(0)

            # The sensor does not record rainfall or wind speed
            df['Rainfall'] = 0.0
            df['Wind'] = 0.0

            cls._df = df[['DateTime', 'Timestamp', 'Temperature',
                          'Humidity', 'Rainfall', 'Wind', 'Solar']]
        except Exception as e:
            print(f"Error loading sensor data: {e}")
            cls._df = pd.DataFrame(
                columns=['DateTime', 'Timestamp', 'Temperature',
                         'Humidity', 'Rainfall', 'Wind', 'Solar']
            )
        return cls._df

    @staticmethod
    def get_current_time_str():
        """Get current time as HH:MM string."""
        return datetime.now().strftime("%H:%M")

    @classmethod
    def get_live_readings(cls):
        """Get current live sensor readings."""
        df = cls._load_main_data()
        now = datetime.now()
        now_str = now.strftime("%H:%M")
        hour = now.hour

        if df.empty:
            return {
                "temperature": 0,
                "humidity": 0,
                "rainfall": 0,
                "wind_speed": 0,
                "solar_radiation": 0,
                "wind_direction": 0,
                "time": now_str,
            }

        # Prefer the most recent row whose HH:MM matches the wall clock;
        # fall back to the very last sensor reading.
        matches = df[df['Timestamp'] == now_str]
        row = matches.iloc[-1] if not matches.empty else df.iloc[-1]

        # Resolve solar separately so daytime never reports a flat 0 just
        # because the most recent recorded row happens to be pre-dawn.
        solar_val = float(row.get("Solar", 0))
        if 6 <= hour <= 18 and solar_val == 0:
            # 1) Try the most recent matching HH:MM row that is non-zero.
            non_zero_match = matches[matches['Solar'] > 0] if not matches.empty else matches
            if not non_zero_match.empty:
                solar_val = float(non_zero_match.iloc[-1]['Solar'])
            else:
                # 2) Fall back to a recent sample from the same hour-of-day.
                same_hour = df[(df['DateTime'].dt.hour == hour) & (df['Solar'] > 0)]
                if not same_hour.empty:
                    solar_val = float(same_hour.iloc[-1]['Solar'])

        return {
            "temperature": round(float(row.get("Temperature", 0)), 2),
            "humidity": round(float(row.get("Humidity", 0)), 2),
            "rainfall": round(float(row.get("Rainfall", 0)), 2),
            "wind_speed": round(float(row.get("Wind", 0)), 2),
            "solar_radiation": round(solar_val, 2),
            "wind_direction": int(np.random.randint(0, 360)),
            "time": now_str,
        }

    @classmethod
    def get_dashboard_data(cls, minutes=60):
        """Get dashboard data for the specified interval (in minutes)."""
        df = cls._load_main_data()

        try:
            if df.empty:
                return [], {}

            minutes_needed = validate_interval(minutes)
            current_time = cls.get_current_time_str()
            now_matches = df[df['Timestamp'] == current_time]

            if not now_matches.empty:
                start_idx = int(now_matches.index[-1])
            else:
                start_idx = max(0, len(df) - 1)

            end_idx = start_idx + minutes_needed

            if end_idx <= len(df):
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
                    "wind_direction": np.random.randint(
                        0, 360, size=len(subset)
                    ).tolist(),
                }
            )
        except Exception as e:
            print(f"Error in get_dashboard_data: {e}")
            return [], {}

    @classmethod
    def get_dashboard_data_range(cls, start_date_str, end_date_str, interval=60):
        """Get dashboard data for a date range using the sensor history."""
        df = cls._load_main_data()

        try:
            if df.empty:
                return [], {}

            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")

            # Limit to max 7 days
            if (end_dt - start_dt).days > 7:
                end_dt = start_dt + timedelta(days=7)

            interval = validate_interval(interval)
            step_minutes = interval if interval < 60 else max(1, interval)

            # Pre-index sensor rows by HH:MM for fast time-of-day lookup.
            # If the requested date is within the recorded history, prefer
            # the actual recorded row for that exact datetime.
            sensor_by_dt = {
                dt.strftime("%Y-%m-%d %H:%M"): row
                for dt, row in zip(df['DateTime'], df.itertuples(index=False))
            }
            sensor_by_time = {}
            for row in df.itertuples(index=False):
                sensor_by_time.setdefault(row.Timestamp, row)

            timestamps = []
            temps, hums, rains, winds, solars, dirs = [], [], [], [], [], []

            current = start_dt
            end_window = end_dt + timedelta(hours=23, minutes=59)

            while current <= end_window:
                if step_minutes >= 60:
                    rounded = current.replace(minute=0, second=0, microsecond=0)
                else:
                    rounded = current.replace(second=0, microsecond=0)

                dt_str = rounded.strftime("%Y-%m-%d %H:%M")
                row = sensor_by_dt.get(dt_str)

                if row is None:
                    # Fall back to time-of-day match from the recorded history
                    row = sensor_by_time.get(rounded.strftime("%H:%M"))

                if row is not None:
                    timestamps.append(dt_str)
                    temps.append(float(row.Temperature))
                    hums.append(float(row.Humidity))
                    rains.append(float(row.Rainfall))
                    winds.append(float(row.Wind))
                    solars.append(float(row.Solar))
                    dirs.append(int(np.random.randint(0, 360)))

                current += timedelta(minutes=step_minutes)

            return (
                timestamps,
                {
                    "temperature": temps,
                    "humidity": hums,
                    "rainfall": rains,
                    "wind": winds,
                    "solar": solars,
                    "wind_direction": dirs,
                }
            )
        except Exception as e:
            print(f"Error in get_dashboard_data_range: {e}")
            return [], {}
