import re
import os
import subprocess

with open('tracking_app/templates/tracking_app/pitch.html', 'r') as f:
    html = f.read()

html = html.replace('{% load static %}', '')
html = re.sub(r"{% static 'tracking_app/assets/(.*?)' %}", r"file:///Users/jmartin/Documents/GitHub/ATS-CRM-Protingent/app_track/tracking_app/static/tracking_app/assets/\1", html)
html = html.replace("{% url 'register' %}", "https://transform.io/register")

with open('raw_pitch.html', 'w') as f:
    f.write(html)

print("Generated raw_pitch.html, running Chrome...")
subprocess.run([
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", 
    "--headless", 
    "--print-to-pdf=Transform_io_SalesPitch.pdf", 
    "--no-pdf-header-footer", 
    "raw_pitch.html"
])
print("Done!")
