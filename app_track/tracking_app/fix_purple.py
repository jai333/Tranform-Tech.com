with open('templates/tracking_app/home.html', 'r') as f:
    content = f.read()

# Replace HTML usages
content = content.replace('fc-icon-purple', 'fc-icon-blue')
content = content.replace('label-purple', 'label-cyan')
content = content.replace('pillar-purple', 'pillar-blue')

# Fix ATS Showcase glow color explicitly if there is an inline style
content = content.replace('<i class=\'bx bx-brain\' style="color:#8b5cf6;"></i>', '<i class=\'bx bx-brain\' style="color:#06b6d4;"></i>')

# Now fix bp-ic-recruit and bp-ic-ats background/color in CSS
content = content.replace('.bp-ic-recruit { background: rgba(139,92,246,0.1); color: #a78bfa; }', '.bp-ic-recruit { background: rgba(6,182,212,0.1); color: #06b6d4; }')
content = content.replace('.bp-ic-ats { background: rgba(99,102,241,0.1); color: #818cf8; }', '.bp-ic-ats { background: rgba(6,182,212,0.1); color: #06b6d4; }')

# Fix inline hover borders for pillar cards
content = content.replace('.pillar-card:hover { border-left-color: #6366f1; }', '.pillar-card:hover { border-left-color: #06b6d4; }')
content = content.replace('.pillar-card:nth-child(2):hover { border-left-color: #a78bfa; }', '.pillar-card:nth-child(2):hover { border-left-color: #06b6d4; }')

# Define pillar-blue if missing
if ".pillar-blue {" not in content:
    content = content.replace('.pillar-red {', '.pillar-blue { background: rgba(6,182,212,0.1) !important; color: #06b6d4 !important; }\n.pillar-red {')

with open('templates/tracking_app/home.html', 'w') as f:
    f.write(content)
