// ── Theme toggle logic ──
document.addEventListener('DOMContentLoaded', () => {
    const themeToggles = document.querySelectorAll('#theme-toggle');
    const themeIcons = document.querySelectorAll('#theme-icon');
    const bodyElement = document.body;

    function applyTheme(theme) {
        if (theme === 'light') {
            bodyElement.classList.add('light-theme');
            document.documentElement.classList.add('light-theme');
            themeIcons.forEach(icon => {
                icon.className = 'fas fa-sun';
                icon.style.color = '#f59e0b';
            });
            themeToggles.forEach(t => t.title = 'Switch to dark mode');
        } else {
            bodyElement.classList.remove('light-theme');
            document.documentElement.classList.remove('light-theme');
            themeIcons.forEach(icon => {
                icon.className = 'fas fa-moon';
                icon.style.color = '';
            });
            themeToggles.forEach(t => t.title = 'Switch to light mode');
        }
    }

    applyTheme(localStorage.getItem('theme') || 'dark');

    themeToggles.forEach(toggle => {
        toggle.addEventListener('click', function () {
            const isLight = bodyElement.classList.contains('light-theme');
            const newTheme = isLight ? 'dark' : 'light';
            localStorage.setItem('theme', newTheme);
            applyTheme(newTheme);
            toggle.style.transform = 'scale(0.85) rotate(25deg)';
            setTimeout(() => { toggle.style.transform = ''; }, 250);
        });
    });

    // Navbar scroll
    const nav = document.querySelector('.navbar');
    if (nav) {
        window.addEventListener('scroll', () => {
            if(window.scrollY > 10) {
                nav.style.borderBottom = "1px solid var(--primary)";
                nav.style.boxShadow = "0 4px 20px rgba(0, 229, 255, 0.05)";
            } else {
                nav.style.borderBottom = "1px solid var(--secondary)";
                nav.style.boxShadow = "none";
            }
        });
    }

    // Typewriter / Terminal Effect
    const termBody = document.getElementById('typewriter-log');
    if (termBody) {
        const logs = [
            "> INIT tx_core_engine v4.0.0",
            "> loading modules... [OK]",
            "> connecting to cluster [us-east-1]... [OK]",
            "> [INFO] Securing endpoint auth via zero-trust policy",
            "> [WARN] 3 CVEs detected on host 10.0.0.42",
            "> [ACTION] Deploying auto-remediation script...",
            "> [SUCCESS] Patch applied. Vulnerability mitigated.",
            "> [INFO] Fetching frontend build status (Next.js)... [OK]",
            "> [SYS] All systems optimized and running at 100% capacity."
        ];

        let i = 0;
        let l = 0;
        
        function typeLine() {
            if (l >= logs.length) {
                setTimeout(() => {
                    termBody.innerHTML = "";
                    l = 0;
                    typeLine();
                }, 5000);
                return;
            }

            const lineData = logs[l];
            let p = document.createElement('p');
            p.style.marginBottom = "4px";
            if (lineData.includes('WARN')) p.style.color = 'var(--accent-yellow)';
            if (lineData.includes('ACTION')) p.style.color = 'var(--accent-red)';
            if (lineData.includes('SUCCESS')) p.style.color = 'var(--accent-green)';

            termBody.appendChild(p);

            function typeChar() {
                if (i < lineData.length) {
                    p.innerHTML += lineData.charAt(i);
                    i++;
                    termBody.scrollTop = termBody.scrollHeight;
                    setTimeout(typeChar, Math.random() * 30 + 10);
                } else {
                    i = 0;
                    l++;
                    setTimeout(typeLine, Math.random() * 600 + 200);
                }
            }
            typeChar();
        }

        setTimeout(typeLine, 1000);
    }
});
