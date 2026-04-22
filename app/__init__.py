"""Flask application factory."""
import os
from flask import Flask
from flask_cors import CORS
from app.routes import main_bp, api_bp


def create_app(config=None):
    """Create and configure Flask application."""
    
    # Get the base directory (project root)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # ✅ FIRST create app
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static'),
        instance_relative_config=True
    )

    # ✅ THEN apply extensions
    CORS(app)

    # Configuration
    app.config['JSON_SORT_KEYS'] = False
    
    if config:
        app.config.update(config)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    
    return app