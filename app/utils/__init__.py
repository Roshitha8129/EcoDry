"""Utility helper functions."""
from datetime import datetime


def parse_date(date_str):
    """Parse date string in YYYY-MM-DD format.
    
    Args:
        date_str: Date string in format YYYY-MM-DD
        
    Returns:
        datetime object or None if parsing fails
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def parse_datetime(date_str, time_str, am_pm=""):
    """Parse date and time strings into datetime object.
    
    Args:
        date_str: Date string in format YYYY-MM-DD
        time_str: Time string in format HH:MM
        am_pm: Optional AM/PM indicator (for 12-hour format)
        
    Returns:
        datetime object or None if parsing fails
    """
    try:
        if am_pm:
            datetime_str = f"{date_str} {time_str} {am_pm}"
            return datetime.strptime(datetime_str, "%Y-%m-%d %I:%M %p")
        else:
            datetime_str = f"{date_str} {time_str}:00"
            return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def round_metric(value, decimals=2):
    """Round metric value to specified decimal places.
    
    Args:
        value: Value to round
        decimals: Number of decimal places
        
    Returns:
        Rounded value or 0 if value is None
    """
    if value is None:
        return 0
    return round(float(value), decimals)


def format_time_str(dt):
    """Format datetime as HH:MM string.
    
    Args:
        dt: datetime object
        
    Returns:
        Time string in format HH:MM
    """
    if not dt:
        return ""
    return dt.strftime("%H:%M")


def format_date_str(dt):
    """Format datetime as YYYY-MM-DD string.
    
    Args:
        dt: datetime object
        
    Returns:
        Date string in format YYYY-MM-DD
    """
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d")


def validate_thickness(thickness):
    """Validate thickness value.
    
    Args:
        thickness: Thickness value to validate
        
    Returns:
        Validated thickness value or None if invalid
    """
    try:
        val = float(thickness)
        if val > 0:
            return val
    except (ValueError, TypeError):
        pass
    return None


def validate_temperature(temp):
    """Validate temperature value.
    
    Args:
        temp: Temperature value to validate
        
    Returns:
        Validated temperature value or default (40) if invalid
    """
    try:
        val = float(temp)
        return val
    except (ValueError, TypeError):
        return 40  # Default temperature


def validate_interval(interval):
    """Validate interval value.
    
    Args:
        interval: Interval in minutes
        
    Returns:
        Validated interval or default (60) if invalid
    """
    try:
        val = int(interval)
        if val > 0:
            return val
    except (ValueError, TypeError):
        pass
    return 60  # Default interval
