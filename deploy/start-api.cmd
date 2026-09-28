@echo off
cd /d E:\websites\news-intelligence\backend
E:\websites\news-intelligence\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 >> E:\websites\news-intelligence\api.log 2>&1
