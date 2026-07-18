with open('tracking_app/templates/tracking_app/home.html', 'r') as f:
    content = f.read()

# Fix btn-showcase-indigo red hex codes
content = content.replace(
    ".btn-showcase-indigo { background: linear-gradient(135deg, #dc2626, #ef4444) !important; box-shadow: 0 4px 20px rgba(239,68,68,0.3) !important; }",
    ".btn-showcase-indigo { background: linear-gradient(135deg, #6366f1, #4f46e5) !important; box-shadow: 0 4px 20px rgba(99,102,241,0.3) !important; }"
)
content = content.replace(
    ".btn-showcase-indigo:hover { box-shadow: 0 8px 32px rgba(239,68,68,0.5) !important; }",
    ".btn-showcase-indigo:hover { box-shadow: 0 8px 32px rgba(99,102,241,0.5) !important; }"
)

# Ensure .sc-indigo has correct color
if '.sc-indigo {' not in content:
    content = content.replace(
        ".sc-red { background: rgba(239,68,68,0.1) !important; color: #ef4444 !important; }",
        ".sc-red { background: rgba(239,68,68,0.1) !important; color: #ef4444 !important; }\n.sc-indigo { background: rgba(99,102,241,0.1) !important; color: #818cf8 !important; }"
    )

with open('tracking_app/templates/tracking_app/home.html', 'w') as f:
    f.write(content)
