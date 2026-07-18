with open('templates/tracking_app/home.html', 'r') as f:
    content = f.read()

# Revert HTML usages specifically
content = content.replace('<div class="label-tag label-cyan">ATS-CRM + INTERVIEW SUITE</div>', '<div class="label-tag label-purple">ATS-CRM + INTERVIEW SUITE</div>')
content = content.replace('<div class="fc-icon fc-icon-blue"><i class=\'bx bx-brain\'></i></div>', '<div class="fc-icon fc-icon-purple"><i class=\'bx bx-brain\'></i></div>')
content = content.replace('<div class="pillar-icon pillar-blue"><i class=\'bx bx-bot\'></i></div>', '<div class="pillar-icon pillar-purple"><i class=\'bx bx-bot\'></i></div>')

# Fix ATS Showcase glow color explicitly if there is an inline style
content = content.replace('<i class=\'bx bx-brain\' style="color:#06b6d4;"></i>', '<i class=\'bx bx-brain\' style="color:#8b5cf6;"></i>')

# Now fix bp-ic-recruit and bp-ic-ats background/color in CSS
content = content.replace('.bp-ic-recruit { background: rgba(6,182,212,0.1); color: #06b6d4; }', '.bp-ic-recruit { background: rgba(139,92,246,0.1); color: #a78bfa; }')
content = content.replace('.bp-ic-ats { background: rgba(6,182,212,0.1); color: #06b6d4; }', '.bp-ic-ats { background: rgba(99,102,241,0.1); color: #818cf8; }')

# Fix inline hover borders for pillar cards
content = content.replace('.pillar-card:hover { border-left-color: #06b6d4; }', '.pillar-card:hover { border-left-color: #6366f1; }')
content = content.replace('.pillar-card:nth-child(2):hover { border-left-color: #06b6d4; }', '.pillar-card:nth-child(2):hover { border-left-color: #a78bfa; }')

with open('templates/tracking_app/home.html', 'w') as f:
    f.write(content)
