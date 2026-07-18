import re

files = [
    'templates/tracking_app/base.html',
    'templates/tracking_app/base_public.html'
]

htmx_script = '<script src="https://unpkg.com/htmx.org@1.9.10"></script>'
htmx_indicator_css = """
    <style>
    .htmx-indicator {
        opacity: 0;
        transition: opacity 200ms ease-in;
    }
    .htmx-request .htmx-indicator {
        opacity: 1;
    }
    .htmx-request.htmx-indicator {
        opacity: 1;
    }
    </style>
"""

for filepath in files:
    with open(filepath, 'r') as f:
        content = f.read()
    
    if "htmx.org" not in content:
        # Add script to head
        head_end = content.find('</head>')
        if head_end != -1:
            content = content[:head_end] + f"    {htmx_script}\n{htmx_indicator_css}\n" + content[head_end:]
        
        # Add hx-boost="true" to body tag
        body_pattern = r'<body([^>]*)>'
        content = re.sub(body_pattern, r'<body\1 hx-boost="true">', content, count=1)
        
        # Also integrate the existing #instant-loader with HTMX
        # It's better to trigger the loader on htmx:beforeRequest and hide on htmx:afterOnLoad
        loader_script = """
    <script>
        document.body.addEventListener('htmx:beforeRequest', function() {
            const loader = document.getElementById('instant-loader');
            if(loader) { loader.style.opacity = '1'; loader.style.width = '30%'; }
        });
        document.body.addEventListener('htmx:afterOnLoad', function() {
            const loader = document.getElementById('instant-loader');
            if(loader) {
                loader.style.width = '100%';
                setTimeout(() => {
                    loader.style.opacity = '0';
                    setTimeout(() => { loader.style.width = '0'; }, 300);
                }, 200);
            }
        });
    </script>
    </body>
"""
        content = content.replace("</body>", loader_script)

        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Updated {filepath} with HTMX")

