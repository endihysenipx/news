@echo off
cd /d E:\websites\news-intelligence\frontend
"C:\Program Files\nodejs\node.exe" node_modules\next\dist\bin\next start --hostname 127.0.0.1 --port 3101 >> E:\websites\news-intelligence\web.log 2>&1
