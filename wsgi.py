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
