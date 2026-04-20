import sys
import os
from flask import Flask, render_template, jsonify, request

# Set up paths for nested backend
base_dir = os.path.dirname(os.path.abspath(__file__))
nested_dir = os.path.join(base_dir, 'updated_inte_pro', 'updated_inte_pro', 'inte', 'inte')
sys.path.insert(0, os.path.join(nested_dir, 'backend'))

# Create Flask app with correct template and static folders
app = Flask(
    __name__,
    template_folder=os.path.join(nested_dir, 'templates'),
    static_folder=os.path.join(nested_dir, 'static')
)

from weather_backend import get_live_readings, get_dashboard_data, get_forecast, get_dashboard_data_range

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/forecasting")
def forecasting():
    return render_template("forecasting.html")

@app.route("/drying-info")
def drying_info():
    return render_template("drying_info.html")

@app.route("/api/live")
def live_data():
    return jsonify(get_live_readings())

@app.route("/api/dashboard")
def dashboard_data():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    interval = int(request.args.get("interval", 60))
    
    if start_date and end_date:
        timestamps, data = get_dashboard_data_range(start_date, end_date, interval)
    else:
        timestamps, data = get_dashboard_data(interval)
        
    return jsonify({
        "timestamps": timestamps,
        "data": data
    })

@app.route("/api/forecast")
def get_forecast_api():
    date = request.args.get("date")
    time = request.args.get("time")
    am_pm = request.args.get("am_pm")
    horizon_raw = request.args.get("horizon", request.args.get("hours", "1"))
    try:
        horizon = int(horizon_raw)
    except Exception:
        horizon = 1
    
    result = get_forecast(date, time, am_pm, hours=horizon)
    if result:
        return jsonify(result)
    else:
        return jsonify({"error": "Data unavailable"}), 404

@app.route("/api/chatbot", methods=["POST"])
def chatbot_api():
    try:
        data = request.json
        user_message = data.get("message", "").lower().strip()
        
        if not user_message:
            return jsonify({"response": "Please ask me something about the drying conditions."}), 400
        
        # Get current live data
        live_data = get_live_readings()
        temp = live_data.get("temperature", 0)
        humidity = live_data.get("humidity", 0)
        solar = live_data.get("solar_radiation", 0)
        rain = live_data.get("rainfall", 0)
        wind = live_data.get("wind_speed", 0)
        
        # Generate response based on user query and real data
        response = generate_bot_response(user_message, temp, humidity, solar, rain, wind)
        
        return jsonify({"response": response}), 200
    except Exception as e:
        return jsonify({"response": "Error processing your query. Please try again.", "error": str(e)}), 500

def generate_bot_response(user_input, temp, humidity, solar, rain, wind):
    """Generate intelligent chatbot responses based on real sensor data"""
    
    # Greetings
    if any(word in user_input for word in ['hello', 'hi', 'hey', 'greetings']):
        return f"👋 Hello! I'm DryBot. Current conditions: {temp}°C, {humidity}% humidity, {solar} W/m² solar. How can I help you optimize your drying?"
    
    # Current drying conditions
    if any(word in user_input for word in ['current', 'condition', 'status', 'how are', 'environment']):
        condition = "favorable" if solar > 600 else "moderate" if solar > 400 else "poor"
        return f"📊 Current conditions are {condition} for drying. Temperature: {temp}°C, Humidity: {humidity}%, Solar: {solar} W/m². {'Excellent!' if condition == 'favorable' else 'Could be better. Consider improvements.' if condition == 'moderate' else 'Suboptimal - add heat or ventilation.'}"
    
    # Temperature queries
    if any(word in user_input for word in ['temperature', 'temp', 'hot', 'cold', 'warm']):
        if temp < 15:
            return f"🌡️ Current temperature is {temp}°C - too cold for efficient drying. Heat input needed."
        elif temp < 25:
            return f"🌡️ Temperature is {temp}°C - acceptable but could be warmer. Ideal range is 25-35°C."
        elif temp < 35:
            return f"🌡️ Perfect! Temperature is {temp}°C - ideal for drying."
        else:
            return f"🌡️ Temperature is {temp}°C - quite high. Monitor product to prevent over-drying."
    
    # Humidity queries
    if any(word in user_input for word in ['humidity', 'moist', 'moisture', 'humid', '% ']):
        if humidity < 40:
            return f"💧 Humidity is {humidity}% - excellent for drying! Low moisture content."
        elif humidity < 60:
            return f"💧 Humidity is {humidity}% - good drying conditions."
        elif humidity < 75:
            return f"💧 Humidity is {humidity}% - moderate. Acceptable but could be drier."
        else:
            return f"💧 Humidity is {humidity}% - quite high! Increase ventilation or add heat urgently."
    
    # Solar radiation queries
    if any(word in user_input for word in ['solar', 'sun', 'radiation', 'light', 'bright']):
        if solar > 600:
            return f"☀️ Solar radiation is {solar} W/m² - excellent! Maximum natural drying power."
        elif solar > 400:
            return f"☀️ Solar radiation is {solar} W/m² - good for drying."
        elif solar > 200:
            return f"☀️ Solar radiation is {solar} W/m² - moderate. Consider supplemental heat."
        else:
            return f"☀️ Solar radiation is {solar} W/m² - low. Active heating recommended."
    
    # Drying time estimation
    if any(word in user_input for word in ['how long', 'duration', 'time', 'take', 'eta']):
        if temp > 30 and humidity < 50 and solar > 600:
            return "⏱️ Estimated drying time: 12-24 hours - Excellent conditions!"
        elif temp > 25 and humidity < 60 and solar > 400:
            return "⏱️ Estimated drying time: 24-36 hours - Good conditions."
        elif temp > 20 and humidity < 70:
            return "⏱️ Estimated drying time: 36-48 hours - Acceptable conditions."
        else:
            return "⏱️ Estimated drying time: 48+ hours - Suboptimal conditions. Improve environment for faster drying."
    
    # Suitability for drying
    if any(word in user_input for word in ['suitable', 'can i dry', 'should i', 'recommend', 'advice', 'suggest']):
        if temp > 25 and humidity < 60 and solar > 400:
            return "✅ YES! Current conditions are suitable for drying. Temperature, humidity, and solar radiation are all favorable. Proceed with drying!"
        elif temp > 20 and humidity < 70:
            return "✓ MAYBE - Conditions are acceptable but not optimal. You can dry but expect slower results. Consider improvements."
        else:
            return "❌ NOT IDEAL - Current conditions are suboptimal for drying. Temperature too low, humidity too high, or insufficient sun. Wait or add artificial heating/ventilation."
    
    # Recommendations
    if any(word in user_input for word in ['recommend', 'improve', 'optimize', 'better', 'help']):
        suggestions = []
        if temp < 25:
            suggestions.append(f"Increase temperature (now {temp}°C, target 25-35°C)")
        if humidity > 60:
            suggestions.append(f"Reduce humidity (now {humidity}%, target <60%)")
        if solar < 400:
            suggestions.append(f"Increase solar exposure or add heat (now {solar} W/m²)")
        
        if suggestions:
            return "💡 Recommendations:\n• " + "\n• ".join(suggestions)
        else:
            return "✓ Conditions are already optimal! Maintain current settings and monitor regularly."
    
    # Forecast predictions
    if any(word in user_input for word in ['predict', 'forecast', 'future', 'tomorrow', 'later']):
        return "🔮 Forecast data available in the Forecasting page. Check there for detailed predictions of temperature, humidity, and solar radiation."
    
    # Help
    if any(word in user_input for word in ['help', 'what can', 'how to', 'tell me']):
        return "ℹ️ I can help you with:\n• Current drying conditions\n• Temperature, humidity, solar data\n• Drying time estimates\n• Whether conditions are suitable for drying\n• Optimization recommendations\n\nJust ask! 😊"
    
    # Default response
    return "🤔 I'm not sure. Try asking about: current conditions, temperature, humidity, solar radiation, drying time, or recommendations!"

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False') == 'True'
    app.run(host='0.0.0.0', port=port, debug=debug)
