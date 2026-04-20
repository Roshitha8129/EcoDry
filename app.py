import sys
import os
import importlib.util

# Find the nested Flask app
base_dir = os.path.dirname(os.path.abspath(__file__))

# Try multiple possible paths
possible_paths = [
    os.path.join(base_dir, 'updated_inte_pro', 'updated_inte_pro', 'inte', 'inte', 'app.py'),
    os.path.join(base_dir, 'inte', 'inte', 'app.py'),
    os.path.join(base_dir, 'updated_inte_pro', 'inte', 'app.py'),
]

nested_app_file = None
app_dir = None

for path in possible_paths:
    if os.path.exists(path):
        nested_app_file = path
        app_dir = os.path.dirname(path)
        break

if not nested_app_file:
    raise FileNotFoundError(f"Could not find Flask app.py in any of these locations: {possible_paths}")

# Change to app directory so relative imports work
os.chdir(app_dir)
sys.path.insert(0, app_dir)

# Load Flask app module directly to avoid circular import
spec = importlib.util.spec_from_file_location("flask_app_module", nested_app_file)
flask_app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flask_app_module)

# Get the Flask app
app = flask_app_module.app

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


import sys
import os

# Add the nested app directory to Python path
app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'updated_inte_pro', 'updated_inte_pro', 'inte', 'inte')
sys.path.insert(0, app_dir)
os.chdir(app_dir)

# Import the Flask app from nested directory
from app import app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
