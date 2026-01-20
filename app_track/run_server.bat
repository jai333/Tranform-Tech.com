@echo off
REM ========================================
REM ATS & CRM Application Server Startup
REM ========================================
echo.
echo ========================================
echo  ATS & CRM with AI/ML Features
echo ========================================
echo.

REM Change to app_track directory
cd /d "%~dp0"

REM Activate virtual environment
call .\.venv\Scripts\activate.bat

REM Set Django settings
set DJANGO_SETTINGS_MODULE=ats_crm_project.settings

REM Start the server
echo Starting Django WSGI Server...
echo.
python -c "
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_crm_project.settings')
import django
django.setup()
from django.core.wsgi import get_wsgi_application
from wsgiref.simple_server import make_server
print('✅ Server is running at http://127.0.0.1:8000/')
print('')
print('Access your application:')
print('  🌐 Home: http://localhost:8000/')
print('  👥 Candidates (with AI): http://localhost:8000/candidates/')
print('  💼 Jobs: http://localhost:8000/jobs/')
print('')
print('AI/ML Features:')
print('  ✨ Resume Parsing')
print('  ✨ Job Matching')
print('  ✨ AI Summaries')
print('  ✨ Advanced Search')
print('  ✨ API Integrations')
print('')
print('Press Ctrl+C to stop the server')
print('-' * 50)
print('')
sys.stdout.flush()
app = get_wsgi_application()
server = make_server('127.0.0.1', 8000, app)
server.serve_forever()
"

pause
