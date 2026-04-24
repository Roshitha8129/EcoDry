"""API routes blueprint."""
from flask import Blueprint, jsonify, request
from app.services.data_service import DataService
from app.services.forecast_service import ForecastService
from app.services.summary_service import SummaryService
from app.utils import validate_interval

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/live', methods=['GET'])
def get_live():
    """Get current live sensor readings.
    
    Returns:
        JSON with current sensor values
    """
    try:
        data = DataService.get_live_readings()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Get dashboard data with optional date range.
    
    Query params:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        interval: Time interval in minutes (default 60)
    
    Returns:
        JSON with timestamps and data arrays
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        interval = validate_interval(request.args.get('interval', 60))
        
        # Use date range if provided
        if start_date and end_date:
            timestamps, data = DataService.get_dashboard_data_range(
                start_date, end_date, interval
            )
        else:
            timestamps, data = DataService.get_dashboard_data(interval)
        
        return jsonify({
            "timestamps": timestamps,
            "data": data
        })
    except Exception as e:
        import traceback
        print(f"Error in dashboard API: {e}")
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "timestamps": [],
            "data": {}
        }), 500


@api_bp.route('/forecast', methods=['GET'])
def get_forecast():
    """Get forecast for specific date, time, and horizon.
    
    Query params:
        date: Date (YYYY-MM-DD)
        time: Time (HH:MM)
        am_pm: AM/PM indicator
        horizon: Forecast horizon in hours (default 1)
    
    Returns:
        JSON with forecast data
    """
    try:
        date_val = request.args.get('date')
        time_val = request.args.get('time')
        am_pm = request.args.get('am_pm', '')
        horizon = request.args.get('horizon', request.args.get('hours', 1))
        
        result = ForecastService.get_forecast(date_val, time_val, am_pm, 
                                             hours=int(horizon))
        
        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "Data unavailable"}), 404
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route('/summary', methods=['GET'])
def get_summary():
    """Get environmental summary for date range.
    
    Query params:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        interval: Time interval in minutes (default 60)
    
    Returns:
        JSON with summary assessment
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        interval = validate_interval(request.args.get('interval', 60))
        
        if not start_date or not end_date:
            return jsonify({
                "error": "start_date and end_date are required"
            }), 400
        
        # Get data for the selected range
        timestamps, data = DataService.get_dashboard_data_range(
            start_date, end_date, interval
        )
        
        # Generate summary from the data
        summary = SummaryService.generate_summary(timestamps, data)
        
        return jsonify(summary)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

