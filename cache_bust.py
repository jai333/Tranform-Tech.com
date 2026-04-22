import os

templates_dir = '/Users/jmartin/Documents/GitHub/ATS-CRM-Protingent/app_track/tracking_app/templates/tracking_app'

for file in os.listdir(templates_dir):
    if file.endswith('.html'):
        filepath = os.path.join(templates_dir, file)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original = content
        
        # Cache bust the transform.css to force the user's browser to load the 180px padding!
        content = content.replace("?v=333", "?v=334")
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Cache-busted CSS in: {file}")
