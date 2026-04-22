"""Blueprint registration for routes."""
from app.routes.pages import main_bp
from app.routes.api import api_bp

__all__ = ['main_bp', 'api_bp']
