@echo off
echo Installing requirements...
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -r requirements.txt
echo.
echo Starting Flask server...
echo (NOTE: The first time starting up, the XGBoost engine will train the models from scratch)
echo (This usually takes around 30 to 60 seconds. Please wait for the 'Running on http://127.0.0.1:5000' message!)
echo.
python -u app.py
pause

