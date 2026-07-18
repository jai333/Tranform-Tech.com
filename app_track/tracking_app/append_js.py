with open('templates/tracking_app/sales/dashboard.html', 'r') as f:
    content = f.read()

js_snippet = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    const themeToggles = document.querySelectorAll('#theme-toggle');
    const themeIcons = document.querySelectorAll('#theme-icon');
    const rootElement = document.documentElement;
    const bodyElement = document.body;

    function applyTheme(theme) {
        if (theme === 'light') {
            rootElement.classList.add('light-theme');
            bodyElement.classList.add('light-theme');
            themeIcons.forEach(icon => {
                icon.className = 'fas fa-sun';
                icon.style.color = '#f59e0b';
            });
        } else {
            rootElement.classList.remove('light-theme');
            bodyElement.classList.remove('light-theme');
            themeIcons.forEach(icon => {
                icon.className = 'fas fa-moon';
                icon.style.color = '';
            });
        }
    }

    // Set initial icon
    const savedTheme = localStorage.getItem('theme') || 'dark';
    applyTheme(savedTheme);

    themeToggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
            const currentTheme = bodyElement.classList.contains('light-theme') ? 'light' : 'dark';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            localStorage.setItem('theme', newTheme);
            applyTheme(newTheme);
        });
    });
});
</script>
"""

if "const themeToggles = document.querySelectorAll('#theme-toggle');" not in content:
    content = content.replace('</body>', js_snippet + '\\n</body>')
    with open('templates/tracking_app/sales/dashboard.html', 'w') as f:
        f.write(content)
    print("Injected JS into sales/dashboard.html")
else:
    print("JS already exists")
