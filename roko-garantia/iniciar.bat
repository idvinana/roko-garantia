@echo off
REM Desenvolvimento no Windows: 2 backends (APIs) + frontend separado em :3000
cd /d %~dp0
for %%d in (admin-backend verificacao-backend) do (
  if not exist %%d\.env copy %%d\.env.example %%d\.env
  if not exist %%d\venv ( python -m venv %%d\venv && %%d\venv\Scripts\pip install -q -r %%d\requirements.txt )
)
start "verificacao" cmd /k "cd verificacao-backend && for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do set %%a=%%b && venv\Scripts\uvicorn main:app --port 8001"
start "admin" cmd /k "cd admin-backend && for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do set %%a=%%b && venv\Scripts\uvicorn main:app --port 8000"
start "frontend" cmd /k "cd frontend && python -m http.server 3000"
echo Frontend: http://localhost:3000
