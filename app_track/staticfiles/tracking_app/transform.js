// Typewriter / Terminal Effect
document.addEventListener('DOMContentLoaded', () => {
    const termBody = document.getElementById('typewriter-log');
    if (!termBody) return;

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
    
    // Navbar scroll
    const nav = document.querySelector('.navbar');
    window.addEventListener('scroll', () => {
        if(window.scrollY > 10) {
            nav.style.borderBottom = "1px solid var(--primary)";
            nav.style.boxShadow = "0 4px 20px rgba(0, 229, 255, 0.05)";
        } else {
            nav.style.borderBottom = "1px solid var(--secondary)";
            nav.style.boxShadow = "none";
        }
    });
});
