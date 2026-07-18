with open('/Users/jmartin/.gemini/antigravity/brain/aa2b47bc-d9b2-4fd7-af86-2b3012366363/artifacts/task.md', 'r') as f:
    content = f.read()

content = content.replace("- `[ ]` Update `threat_dashboard.html` with Threat Origin Map and metrics", "- `[x]` Update `threat_dashboard.html` with Threat Origin Map and metrics")
content = content.replace("- `[ ]` Update `threat_incident_detail.html` with IoCs and CVSS", "- `[x]` Update `threat_incident_detail.html` with IoCs and CVSS")

with open('/Users/jmartin/.gemini/antigravity/brain/aa2b47bc-d9b2-4fd7-af86-2b3012366363/artifacts/task.md', 'w') as f:
    f.write(content)
