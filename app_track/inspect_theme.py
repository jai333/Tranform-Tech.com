import os
import re

TEMPLATE_DIR = 'tracking_app/templates/tracking_app'

patterns = {
    r'color:\s*(#fff|#ffffff)(;|")': r'color: var(--apple-text)\2',
    r'color:\s*rgba\(255,\s*255,\s*255,\s*0\.[789]\)(;|")': r'color: var(--apple-text-secondary)\1',
    r'color:\s*rgba\(255,\s*255,\s*255,\s*0\.[3456]\)(;|")': r'color: var(--apple-text-muted)\1',
    r'background(-color)?:\s*(#1a1a1a|#1e1e1e|#111111|#09090b|#1e293b|#18181b|#27272a)(;|")': r'background\1: var(--apple-card-bg)\3',
    r'background(-color)?:\s*rgba\(255,\s*255,\s*255,\s*0\.0[1-9]\)(;|")': r'background\1: var(--apple-card-bg-hover)\2',
    r'border(-bottom|-top|-left|-right)?:\s*1px solid rgba\(255,\s*255,\s*255,\s*0\.1[05]?\)(;|")': r'border\1: 1px solid var(--apple-border)\2',
}

files_to_modify = set()
total_replacements = 0

for root, _, files in os.walk(TEMPLATE_DIR):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                content = f.read()
            
            for pat, repl in patterns.items():
                content, count = re.subn(pat, repl, content, flags=re.IGNORECASE)
                total_replacements += count
                if count > 0:
                    files_to_modify.add(filepath)

print(f"Total files to modify: {len(files_to_modify)}")
print(f"Total replacements to make: {total_replacements}")
