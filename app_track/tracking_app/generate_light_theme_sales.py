import re

with open('templates/tracking_app/sales/dashboard.html', 'r') as f:
    content = f.read()

# Find the end of the <style> block
style_end = content.find('</style>')

# We'll inject some light theme overrides just before </style>
light_theme_css = """
/* ── LIGHT THEME OVERRIDES ────────────────────────────── */
body.light-theme .dash-tab.active {
    color: #ffffff;
}
body.light-theme .kpi-val {
    color: #0f172a;
}
body.light-theme .deal-title {
    color: #0f172a;
}
body.light-theme .deal-company {
    color: #475569;
}
body.light-theme .deal-amount {
    color: #0f172a;
}
body.light-theme .chart-title {
    color: #0f172a;
}
body.light-theme .activity-item strong {
    color: #0f172a;
}
body.light-theme .ai-rec-text {
    color: #334155;
}
"""

if "/* ── LIGHT THEME OVERRIDES ────────────────────────────── */" not in content:
    new_content = content[:style_end] + light_theme_css + content[style_end:]
    with open('templates/tracking_app/sales/dashboard.html', 'w') as f:
        f.write(new_content)
    print("Added light theme overrides to dashboard.html")
else:
    print("Already added")
