@echo off
pip install -r requirements.txt
start "" "http://localhost:5000"
python app.py
pause