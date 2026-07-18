with open('tracking_app/templates/tracking_app/home.html', 'r') as f:
    content = f.read()

content = content.replace("src=\"{% static 'tracking_app/assets/it_helpdesk_realistic.jpg' %}\"", "src=\"{% static 'tracking_app/assets/it_helpdesk_ui.jpg' %}\"")

with open('tracking_app/templates/tracking_app/home.html', 'w') as f:
    f.write(content)
