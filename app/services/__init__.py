"""Summary service for environmental assessment."""
import numpy as np
from app.services.data_service import DataService
from app.utils import round_metric


class SummaryService:
    """Service for generating environmental summaries based on data ranges."""
    
    @staticmethod
    def generate_summary(timestamps, data):
        """Generate environmental summary from data.
        
        Args:
            timestamps: List of timestamp strings
            data: Dictionary with metric arrays
            
        Returns:
            Dictionary with summary assessment
        """
        if not timestamps or not data or not data.get('temperature'):
            return SummaryService._default_summary()
        
        try:
            temps = np.array(data.get('temperature', []))
            hums = np.array(data.get('humidity', []))
            solars = np.array(data.get('solar', []))
            
            # Calculate averages
            avg_temp = float(np.mean(temps)) if len(temps) > 0 else 0
            avg_humidity = float(np.mean(hums)) if len(hums) > 0 else 0
            avg_solar = float(np.mean(solars)) if len(solars) > 0 else 0
            
            # Categorize conditions
            temp_status = SummaryService._categorize_temperature(avg_temp)
            humidity_status = SummaryService._categorize_humidity(avg_humidity)
            solar_status = SummaryService._categorize_solar(avg_solar)
            
            # Determine overall suitability
            suitability = SummaryService._determine_suitability(
                temp_status, humidity_status, solar_status
            )
            
            return {
                "temperature": {
                    "value": round_metric(avg_temp),
                    "unit": "°C",
                    "status": temp_status
                },
                "humidity": {
                    "value": round_metric(avg_humidity),
                    "unit": "%",
                    "status": humidity_status
                },
                "solar_radiation": {
                    "value": round_metric(avg_solar),
                    "unit": "W/m²",
                    "status": solar_status
                },
                "suitability": suitability,
                "assessment": SummaryService._get_assessment_text(
                    avg_temp, avg_humidity, avg_solar, suitability
                )
            }
        except Exception as e:
            print(f"Error generating summary: {e}")
            return SummaryService._default_summary()
    
    @staticmethod
    def _categorize_temperature(temp):
        """Categorize temperature condition.
        
        Args:
            temp: Temperature in Celsius
            
        Returns:
            Status string: 'low', 'ideal', or 'high'
        """
        if temp < 25:
            return "low"
        elif temp <= 35:
            return "ideal"
        else:
            return "high"
    
    @staticmethod
    def _categorize_humidity(humidity):
        """Categorize humidity condition.
        
        Args:
            humidity: Humidity percentage
            
        Returns:
            Status string: 'good', 'moderate', or 'high'
        """
        if humidity < 40:
            return "good"
        elif humidity <= 70:
            return "moderate"
        else:
            return "high"
    
    @staticmethod
    def _categorize_solar(solar):
        """Categorize solar radiation condition.
        
        Args:
            solar: Solar radiation in W/m²
            
        Returns:
            Status string: 'low', 'moderate', or 'excellent'
        """
        if solar < 300:
            return "low"
        elif solar <= 600:
            return "moderate"
        else:
            return "excellent"
    
    @staticmethod
    def _determine_suitability(temp_status, humidity_status, solar_status):
        """Determine overall drying suitability.
        
        Args:
            temp_status: Temperature status
            humidity_status: Humidity status
            solar_status: Solar radiation status
            
        Returns:
            Suitability level: 'Favorable', 'Moderate', or 'Unfavorable'
        """
        # Count favorable conditions
        favorable_count = 0
        
        # Temperature: ideal is best, low is okay, high is not ideal
        if temp_status in ['ideal', 'low']:
            favorable_count += 1
        
        # Humidity: good is ideal, moderate is okay
        if humidity_status in ['good', 'moderate']:
            favorable_count += 1
        
        # Solar: excellent is ideal, moderate is okay
        if solar_status in ['excellent', 'moderate']:
            favorable_count += 1
        
        if favorable_count >= 2.5:
            return "Favorable for drying"
        elif favorable_count >= 1.5:
            return "Moderately suitable"
        else:
            return "Not suitable"
    
    @staticmethod
    def _get_assessment_text(temp, humidity, solar, suitability):
        """Generate assessment text based on metrics.
        
        Args:
            temp: Average temperature
            humidity: Average humidity
            solar: Average solar radiation
            suitability: Overall suitability
            
        Returns:
            Assessment text string
        """
        conditions = []
        
        # Temperature assessment
        if temp < 25:
            conditions.append("Temperature is low, which may slow drying")
        elif temp > 35:
            conditions.append("High temperatures detected - monitor product integrity")
        else:
            conditions.append("Temperature is optimal for drying")
        
        # Humidity assessment
        if humidity < 40:
            conditions.append("Low humidity is ideal for drying")
        elif humidity <= 70:
            conditions.append("Moderate humidity levels detected")
        else:
            conditions.append("High humidity may impede drying process")
        
        # Solar radiation assessment
        if solar < 300:
            conditions.append("Low solar radiation - consider supplementary drying")
        elif solar <= 600:
            conditions.append("Moderate solar radiation available")
        else:
            conditions.append("Excellent solar radiation for natural drying")
        
        return " | ".join(conditions)
    
    @staticmethod
    def _default_summary():
        """Return default summary when data unavailable.
        
        Returns:
            Default summary dictionary
        """
        return {
            "temperature": {
                "value": 0,
                "unit": "°C",
                "status": "unknown"
            },
            "humidity": {
                "value": 0,
                "unit": "%",
                "status": "unknown"
            },
            "solar_radiation": {
                "value": 0,
                "unit": "W/m²",
                "status": "unknown"
            },
            "suitability": "Data unavailable",
            "assessment": "Unable to generate assessment - insufficient data"
        }
