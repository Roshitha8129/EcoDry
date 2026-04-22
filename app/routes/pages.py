"""Page routes blueprint."""
from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    """Home page."""
    return render_template('home.html')


@main_bp.route('/dashboard')
def dashboard():
    """Dashboard page."""
    return render_template('dashboard.html')


@main_bp.route('/forecasting')
def forecasting():
    """Forecasting page."""
    return render_template('forecasting.html')


@main_bp.route('/drying-info')
def drying_info():
    """Drying information page."""
    return render_template('drying_info.html')


@main_bp.route('/about')
def about():
    """About page."""
    return render_template('about.html')


@main_bp.route('/settings')
def settings():
    """Settings page."""
    return render_template('settings.html')
