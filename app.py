"""Root Flask application entry point."""
import os
import sys

# # Add the inte folder to path so we can import the app module
# inte_path = os.path.join(os.path.dirname(__file__), 'updated_inte_pro', 'inte')
# sys.path.insert(0, inte_path)

# Import and create the Flask app
from app import create_app

# Create Flask app using app factory pattern
app = create_app()


if __name__ == "__main__":
    # Get port from environment or use default (5000 for Replit)
    port = int(os.environ.get("PORT", 5000))
    
    # Run app
    print(f"Starting EcoDry application on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)