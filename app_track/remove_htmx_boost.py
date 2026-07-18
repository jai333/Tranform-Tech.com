import re

for filename in ['tracking_app/templates/tracking_app/base.html', 'tracking_app/templates/tracking_app/base_public.html']:
    with open(filename, 'r') as f:
        content = f.read()
    
    # Remove hx-boost="true" from body tag
    content = content.replace('<body hx-boost="true">', '<body>')
    
    with open(filename, 'w') as f:
        f.write(content)

