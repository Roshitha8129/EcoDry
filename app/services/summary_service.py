"""Summary service for environmental insights."""

import numpy as np


class SummaryService:
    """Service to generate summary insights from dashboard data."""

    @staticmethod
    def generate_summary(timestamps, data):
        """Generate summary statistics from dashboard data.

        Args:
            timestamps: list of timestamps
            data: dict containing temperature, humidity, etc.

        Returns:
            dict summary
        """
        try:
            if not timestamps or not data:
                return {
                    "message": "No data available",
                    "summary": {}
                }

            def safe_avg(values):
                return round(float(np.mean(values)), 2) if values else 0

            summary = {
                "avg_temperature": safe_avg(data.get("temperature", [])),
                "avg_humidity": safe_avg(data.get("humidity", [])),
                "total_rainfall": round(sum(data.get("rainfall", [])), 2),
                "avg_wind_speed": safe_avg(data.get("wind", [])),
                "avg_solar_radiation": safe_avg(data.get("solar", [])),
                "data_points": len(timestamps)
            }

            return {
                "message": "Summary generated successfully",
                "summary": summary
            }

        except Exception as e:
            return {
                "error": str(e),
                "summary": {}
            }