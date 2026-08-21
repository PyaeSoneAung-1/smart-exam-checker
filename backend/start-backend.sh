#!/bin/bash
cd /www/wwwroot/exam.hiroshi.cloud/backend
source venv/bin/activate
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8090 --workers 1
