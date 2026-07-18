import re

with open('templates/tracking_app/home.html', 'r') as f:
    content = f.read()

# Find the end of the <style> block
style_end = content.find('</style>')

# We'll inject some light theme overrides just before </style>
light_theme_css = """
/* ── LIGHT THEME OVERRIDES ────────────────────────────── */
body.light-theme .hero-cinematic {
    background: #f8fafc;
}
body.light-theme .cine-h1 {
    color: #0f172a;
}
body.light-theme .cine-sub {
    color: #475569;
}
body.light-theme .announce-chip {
    background: rgba(99,102,241,0.1);
    border-color: rgba(99,102,241,0.3);
    color: #4338ca;
}
body.light-theme .trust-text {
    color: #475569;
}
body.light-theme .trust-num {
    color: #0f172a !important;
}
body.light-theme .mockup-frame {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1);
}
body.light-theme .float-card {
    background: rgba(255, 255, 255, 0.9);
    border: 1px solid #e2e8f0;
    box-shadow: 0 10px 25px rgba(0,0,0,0.05);
}
body.light-theme .fc-num {
    color: #0f172a;
}
body.light-theme .fc-label {
    color: #64748b;
}
body.light-theme .huge-title {
    color: #0f172a;
}
body.light-theme .bento-box {
    background: #ffffff;
    border-color: #e2e8f0;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
}
body.light-theme .bento-box:hover {
    border-color: #cbd5e1;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05);
}
body.light-theme .bento-title {
    color: #0f172a;
}
body.light-theme .bento-desc {
    color: #475569;
}
body.light-theme .section-intro p {
    color: #475569;
}
body.light-theme .bp-desc {
    color: #475569;
}
body.light-theme .bp-title {
    color: #0f172a;
}
body.light-theme .stat-block {
    background: #ffffff;
    border-color: #e2e8f0;
}
body.light-theme .stat-val {
    color: #0f172a;
}
body.light-theme .stat-label {
    color: #64748b;
}
body.light-theme .trust-logo-chip {
    border-color: #e2e8f0;
    color: #475569;
}
body.light-theme .tsl-divider {
    background: #e2e8f0;
}
body.light-theme .svc-card {
    background: #ffffff;
    border-color: #e2e8f0;
}
body.light-theme .svc-card:hover {
    background: #f8fafc;
    border-color: #cbd5e1;
}
body.light-theme .svc-title {
    color: #0f172a;
}
body.light-theme .svc-desc {
    color: #475569;
}
body.light-theme .svc-feature {
    color: #475569;
}
body.light-theme .cta-banner {
    background: #ffffff;
    border-color: #e2e8f0;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05);
}
body.light-theme .cta-title {
    color: #0f172a;
}
body.light-theme .cta-desc {
    color: #475569;
}
body.light-theme .footer {
    border-top: 1px solid #e2e8f0;
    background: #f8fafc;
}
body.light-theme .footer p {
    color: #64748b;
}
"""

if "/* ── LIGHT THEME OVERRIDES ────────────────────────────── */" not in content:
    new_content = content[:style_end] + light_theme_css + content[style_end:]
    with open('templates/tracking_app/home.html', 'w') as f:
        f.write(new_content)
    print("Added light theme overrides to home.html")
else:
    print("Already added")
