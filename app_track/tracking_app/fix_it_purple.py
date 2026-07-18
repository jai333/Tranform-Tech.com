with open('templates/tracking_app/it_helpdesk.html', 'r') as f:
    content = f.read()

# Replace purple hex codes with blue/cyan ones
content = content.replace('#6366f1', '#0ea5e9') # sky blue
content = content.replace('rgba(99,102,241,', 'rgba(14,165,233,')

content = content.replace('#a855f7', '#64748b') # slate gray
content = content.replace('rgba(168,85,247,', 'rgba(100,116,139,')

content = content.replace('#a5b4fc', '#94a3b8')
content = content.replace('#c4b5fd', '#cbd5e1')

with open('templates/tracking_app/it_helpdesk.html', 'w') as f:
    f.write(content)
