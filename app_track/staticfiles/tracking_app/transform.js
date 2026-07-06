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
            "> INITIALIZING TRANSFORM.IO UNIFIED PLATFORM v6.0.0...",
            "> [OK] 7 system layers mapped: AI_Sales, Cybersecurity, Recruiting, ATS_CRM, Dev, BI_Dashboards, ITaaS",
            "> [AI_SDR] Syncing lead pipeline endpoints...",
            "> [AI_SDR] SMTP handshake verified (zgih pkfv twli ixrg) - status: connected",
            "> [AI_SDR] Found 26 active outreach targets. Win probability optimized.",
            "> [CYBER] Audit trace: Zero-Trust policies loaded. SOC2 audit grid active.",
            "> [CYBER] Threat scanning: 0 vulnerabilities found. SSL TLS 1.3 verified.",
            "> [ATS_CRM] Parsing CV pipeline... Ingesting resume profiles...",
            "> [ATS_CRM] NLP similarity index: Candidate #841 matches Job description at 94% accuracy.",
            "> [ATS_CRM] Interview scheduler daemon: active. 2 video rounds pending.",
            "> [APP_DEV] Checking Next.js/Django endpoints. DB replica pools synced.",
            "> [ITaaS] Fleet scale checks: AWS k8s cluster online. CPU: 12%, Mem: 22%.",
            "> [SYSTEM] 7 verticals online. Awaiting operator command."
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
            if (lineData.includes('[OK]') || lineData.includes('verified') || lineData.includes('online')) {
                p.style.color = '#34C759'; // accent-green
            } else if (lineData.includes('v6.0.0') || lineData.includes('layers mapped')) {
                p.style.color = '#00E5FF'; // primary cyan
            } else if (lineData.includes('Candidate #841') || lineData.includes('AI_SDR') || lineData.includes('CYBER')) {
                p.style.color = '#a78bfa'; // purple/lavender
            } else {
                p.style.color = '#e2e8f0'; // slate white
            }

            termBody.appendChild(p);

            function typeChar() {
                if (i < lineData.length) {
                    p.innerHTML += lineData.charAt(i);
                    i++;
                    termBody.scrollTop = termBody.scrollHeight;
                    setTimeout(typeChar, Math.random() * 20 + 5);
                } else {
                    i = 0;
                    l++;
                    setTimeout(typeLine, Math.random() * 400 + 100);
                }
            }
            typeChar();
        }

        setTimeout(typeLine, 1000);
    }
});
