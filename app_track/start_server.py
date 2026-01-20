import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'ats_crm_project.settings'

import django
django.setup()

from django.core.wsgi import get_wsgi_application
from wsgiref.simple_server import make_server

app = get_wsgi_application()
server = make_server('127.0.0.1', 8000, app)

print('\n' + '='*60)
print('  ✅ ATS & CRM SERVER STARTED SUCCESSFULLY')
print('='*60)
print('  📍 Server URL: http://127.0.0.1:8000/')
print('  👥 Candidates: http://127.0.0.1:8000/candidates/')
print('  💼 Jobs: http://127.0.0.1:8000/jobs/')
print('  🧠 AI Features: Click brain icon on candidate')
print('='*60)
print('  Press Ctrl+C to stop')
print('='*60 + '\n')

sys.stdout.flush()
server.serve_forever()
