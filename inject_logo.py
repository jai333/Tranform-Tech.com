import os

# Paths
templates_dir = '/Users/jmartin/Documents/GitHub/ATS-CRM-Protingent/app_track/tracking_app/templates/tracking_app'

logo_html = """<img src="{% static \'tracking_app/assets/logo-333.png\' %}" alt="Transform.io 333 Logo" style="height: 48px; width: auto; max-width: 250px; border-radius: 4px; box-shadow: 0 0 10px rgba(0, 229, 255, 0.5);">"""

# Find all HTML files
for file in os.listdir(templates_dir):
    if file.endswith('.html'):
        filepath = os.path.join(templates_dir, file)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original = content
        
        # Replace base.html variant
        content = content.replace("""<i class="fas fa-network-wired" style="color: var(--brand-primary);"></i> TRANSFORM.IO""", logo_html)
        
        # Replace marketing variant
        content = content.replace("""<i class='bx bx-network-chart text-cyan'></i> TRANSFORM.IO""", logo_html)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated logo in: {file}")
