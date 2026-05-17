import os
import re

nav_replacement = """    <!-- Mega-Menu Navigation -->
    <nav class="navbar border-bottom">
        <div class="container nav-content">
            <a href="index.html" class="logo font-mono">
                <i class='bx bx-code-alt text-cyan'></i> TRANSFORM.IO
            </a>
            
            <ul class="nav-links font-mono text-sm">
                <li>
                    <a href="#">PLATFORM <i class='bx bx-chevron-down'></i></a>
                    <div class="mega-menu">
                        <div class="mega-col">
                            <span class="mega-header">CORE SERVICES</span>
                            <a href="ats.html">Applicant Tracking Systems</a>
                            <a href="crm.html">Client CRM Matrix</a>
                            <a href="ai-parsing.html">AI Resume Parsing</a>
                            <a href="workflow.html">Recruitment Automation</a>
                            <a href="dashboards.html">Data Telemetry & Dashboards</a>
                        </div>
                    </div>
                </li>

                <li>
                    <a href="#">SOLUTIONS <i class='bx bx-chevron-down'></i></a>
                    <div class="mega-menu" style="min-width: 400px;">
                        <div class="mega-col">
                            <span class="mega-header">BY INDUSTRY</span>
                            <a href="industry-tech.html">US Tech Staffing</a>
                            <a href="industry-healthcare.html">Healthcare Staffing</a>
                            <a href="industry-exec.html">Executive Search</a>
                        </div>
                        <div class="mega-col">
                            <span class="mega-header">BY ROLE</span>
                            <a href="role-recruiter.html">For Recruiters</a>
                            <a href="role-manager.html">For Account Managers</a>
                            <a href="role-agency.html">For Agency Owners</a>
                        </div>
                    </div>
                </li>

                <li>
                    <a href="#">RESOURCES <i class='bx bx-chevron-down'></i></a>
                    <div class="mega-menu" style="min-width: 400px;">
                        <div class="mega-col">
                            <span class="mega-header">KNOWLEDGE</span>
                            <a href="portfolio.html">Case Studies</a>
                            <a href="blog.html">Recruitment Blog</a>
                        </div>
                    </div>
                </li>
            </ul>

            <a href="#contact" class="btn btn-outline font-mono">/FREE_WORKFLOW_AUDIT</a>
        </div>
    </nav>"""

footer_replacement = """    <!-- Exhaustive NinjaOne Style Footer -->
    <footer class="footer font-mono mt-xl">
        <div class="container footer-mega-grid">
            <div class="footer-brand footer-col">
                <a href="index.html" class="logo text-xl mb-md"><i class='bx bx-code-alt text-cyan'></i> TRANSFORM.IO</a>
                <p class="text-gray text-xs mb-md" style="line-height:1.6;">Automation-driven recruitment infrastructure for US-based staffing companies.</p>
                <div class="social-icons flex gap-sm text-gray text-xl">
                    <i class='bx bxl-linkedin-square'></i>
                    <i class='bx bxl-twitter'></i>
                    <i class='bx bxl-github' ></i>
                </div>
            </div>
            
            <div class="footer-col">
                <h4 class="font-mono text-white">RECRUITMENT</h4>
                <a href="ats.html">ATS Pipelines</a>
                <a href="crm.html">Client CRM</a>
                <a href="ai-parsing.html">AI NLP Parsing</a>
            </div>

            <div class="footer-col">
                <h4 class="font-mono text-white">SOLUTIONS</h4>
                <a href="workflow.html">Workflow Automation</a>
                <a href="dashboards.html">Data Dashboards</a>
            </div>

            <div class="footer-col">
                <h4 class="font-mono text-white">INDUSTRIES</h4>
                <a href="industry-tech.html">Tech Staffing</a>
                <a href="industry-healthcare.html">Healthcare Staffing</a>
            </div>
        </div>

        <div class="container footer-bottom mt-lg" style="border-top: 1px solid #1a1a1a; padding-top: 24px; color: #555;">
            <p>&copy; 2026 Transform.io Technical Solutions.</p>
        </div>
    </footer>"""

page_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>%(title)s | Transform.io</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;600&family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <link href='https://unpkg.com/boxicons@2.1.4/css/boxicons.min.css' rel='stylesheet'>
    <link rel="stylesheet" href="style.css">
    <style>
        .feature-list { list-style: none; margin-top: 16px; padding:0;}
        .feature-list li { display: flex; gap: 12px; margin-bottom: 12px; font-size: 0.95rem; color: var(--text-gray); }
        .feature-list li i { color: var(--primary); font-size: 1.4rem; margin-top: 2px;}
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 48px; }
        .huge-title { font-size: 3rem; letter-spacing: -0.03em; color: white; margin-bottom: 24px; line-height: 1.1; }
        .sub-tag { color: var(--primary); font-family: var(--font-mono); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; display: block; }
        .highlight-box { background: rgba(0, 229, 255, 0.05); border-left: 3px solid var(--primary); padding: 24px; margin: 24px 0; border-radius: 0 8px 8px 0;}
    </style>
</head>
<body>

%(nav)s

    <header class="container pt-xl pb-lg border-bottom">
        <span class="sub-tag">[ %(tag)s ]</span>
        <h1 class="huge-title">%(h1)s</h1>
        <p class="font-mono text-gray" style="font-size:1.1rem; max-width:800px; line-height: 1.6;">
            %(desc)s
        </p>
    </header>

    <section class="container mt-xl mb-xl">
        <div class="grid-2 align-center mb-lg">
            <div>
                <h3 class="text-white text-xl mb-md">%(h3)s</h3>
                <p class="text-gray mb-md line-height-relaxed">
                    %(p1)s
                </p>
                <div class="highlight-box">
                    <p class="font-mono text-white text-sm">"%(quote)s"</p>
                </div>
            </div>
            <div class="grid" style="gap:24px;">
               <div class="border-glow" style="padding: 24px; background:#000;">
                   <h4 class="text-white font-mono text-xs">> %(term_header)s</h4>
                   <p class="font-mono text-xs text-gray mt-sm" style="line-height:2;">
                     %(term_lines)s
                     <span class="text-primary">[SUCCESS] Sequence completed seamlessly.</span>
                   </p>
               </div>
            </div>
        </div>
    </section>

%(footer)s

    <script src="script.js"></script>
</body>
</html>"""

pages_to_create = [
    {
        "filename": "ats.html", "title": "Custom ATS", "tag": "MODULE_01 / ATS", "h1": "Applicant Tracking Architecture",
        "desc": "Drag-and-drop Kanban hiring boards with zero friction. We build ATS platforms that recruiters actually want to use.", "h3": "Pipeline Clarity", "p1": "Stop losing candidates in email threads. Track everything from sourcing to placement visually.", "quote": "Placement speeds increased by 40%.", "term_header": "ATS_SYNC", "term_lines": "[MOVE] Candidate to Interview Stage<br>[SYNC] Calendar updated automatically.<br>"
    },
    {
        "filename": "crm.html", "title": "Client CRM", "tag": "MODULE_02 / CRM", "h1": "Client CRM Matrix",
        "desc": "Real-time pipeline forecasting. Track job orders, client communications, and margins automatically.", "h3": "Sales Velocity", "p1": "Deep visibility into your sales funnel. Never miss a client follow-up again.", "quote": "Total clarity on agency revenue pipelines.", "term_header": "CRM_LOG", "term_lines": "[UPDATE] Job Order Status -> Active<br>[NOTIFY] Sourcing team pinged.<br>"
    },
    {
        "filename": "workflow.html", "title": "Workflow Automation", "tag": "MODULE_03 / AUTOMATION", "h1": "Recruitment Automation",
        "desc": "Automate the busywork. Auto-emailing, auto-scheduling, and auto-reminders.", "h3": "Zero Manual Tasks", "p1": "Let the system handle the follow-ups while your recruiters focus on relationship building.", "quote": "Saved 15 hours per recruiter per week.", "term_header": "AUTO_BOT", "term_lines": "[TRIGGER] Candidate applied.<br>[ACTION] Sending calendar invite.<br>"
    },
    {
        "filename": "ai-parsing.html", "title": "AI Parsing", "tag": "MODULE_04 / NLP", "h1": "AI Resume Parsing",
        "desc": "Semantic NLP parsing logic natively reads through CV fluff and extracts structured data.", "h3": "Deep Matching", "p1": "Uses Cosine Similarity to calculate exact 0-100 match percentages against job descriptions.", "quote": "Identifies the best candidate in seconds.", "term_header": "NLP_ENGINE", "term_lines": "[PARSE] Ingesting PDF file.<br>[EXTRACT] 5 years React experience found.<br>"
    },
    {
        "filename": "dashboards.html", "title": "Data Dashboards", "tag": "MODULE_05 / TELEMETRY", "h1": "Data Telemetry & Dashboards",
        "desc": "Gain full pipeline visibility. Real-time dashboards track placement efficiency and operational KPIs.", "h3": "Executive Command Centers", "p1": "Data is only useful if it's actionable. Monitor your business at a granular level.", "quote": "Absolute visibility into recruiter metrics.", "term_header": "DATA_LOG", "term_lines": "[CALC] Time to fill -> 14 days.<br>[UPDATE] Dashboard refreshed.<br>"
    },
    {
        "filename": "industry-tech.html", "title": "US Tech Staffing", "tag": "INDUSTRY / TECH", "h1": "US Tech Staffing Infrastructure",
        "desc": "Built specifically for the high-velocity demands of US IT and Software Engineering staffing agencies.", "h3": "High-Velocity Hiring", "p1": "We understand the tech stack, the market, and the speed required to win.", "quote": "Placing senior engineers faster than the competition.", "term_header": "TECH_SYNC", "term_lines": "[MATCH] Kubernetes skillset verified.<br>[SUBMIT] Candidate sent to client.<br>"
    },
    {
        "filename": "industry-healthcare.html", "title": "Healthcare Staffing", "tag": "INDUSTRY / HEALTH", "h1": "Healthcare Staffing Logistics",
        "desc": "Manage credentialing, compliance, and shift-based recruitment effortlessly.", "h3": "Credential Tracking", "p1": "Automated alerts for expiring nursing licenses and certifications.", "quote": "100% compliance across all placements.", "term_header": "CRED_CHECK", "term_lines": "[AUDIT] Checking RN license... VALID.<br>[WARN] CPR cert expires in 30 days.<br>"
    },
    {
        "filename": "industry-exec.html", "title": "Executive Search", "tag": "INDUSTRY / EXEC", "h1": "Executive Search Platforms",
        "desc": "White-glove CRM tracking for high-touch, confidential executive placements.", "h3": "Confidential Pipelines", "p1": "Secure, private workflows for C-suite recruitment.", "quote": "Discretion and speed guaranteed.", "term_header": "EXEC_LOG", "term_lines": "[ENCRYPT] Retained search details locked.<br>[SEND] NDA sent to candidate.<br>"
    },
    {
        "filename": "role-recruiter.html", "title": "For Recruiters", "tag": "ROLE / RECRUITER", "h1": "Empowered Recruiters",
        "desc": "Stop fighting your software. We build tools that make your job easier.", "h3": "Focus on Sourcing", "p1": "Consolidate your outreach and tracking into one unified engine.", "quote": "Recruiter morale up 200%.", "term_header": "REC_DASH", "term_lines": "[VIEW] 15 new applicants today.<br>[ACT] Auto-screening initiated.<br>"
    },
    {
        "filename": "role-manager.html", "title": "For Account Managers", "tag": "ROLE / AM", "h1": "Account Manager Matrix",
        "desc": "Never drop the ball on a client. Full visibility into every job order.", "h3": "Client Success", "p1": "Automated reporting and transparent pipelines.", "quote": "Client retention increased by 30%.", "term_header": "AM_VIEW", "term_lines": "[SYNC] Client feedback received.<br>[UPDATE] ATS notes updated.<br>"
    },
    {
        "filename": "role-agency.html", "title": "For Agency Owners", "tag": "ROLE / OWNER", "h1": "Agency Growth Engine",
        "desc": "Scale your firm with infrastructure that doesn't break at 50 recruiters.", "h3": "Predictable Revenue", "p1": "High switching-cost system design ensures your data is a competitive moat.", "quote": "Built to scale to $100M+ ARR.", "term_header": "OWNER_LOG", "term_lines": "[CALC] Monthly placements: 42.<br>[GROW] Infrastructure ready for expansion.<br>"
    },
    {
        "filename": "blog.html", "title": "Recruitment Blog", "tag": "KNOWLEDGE / BLOG", "h1": "Recruitment Intelligence",
        "desc": "Deep dives into staffing workflows, automation strategies, and systemizing your agency.", "h3": "Latest Strategies", "p1": "Read how we helped agencies double their placement velocity.", "quote": "Because data wins.", "term_header": "READ_FILE", "term_lines": "$ cat latest_post.md<br># Automating the follow-up...<br>"
    },
    {
        "filename": "portfolio.html", "title": "Case Studies", "tag": "KNOWLEDGE / CASE", "h1": "Agency Success Stories",
        "desc": "Real results from staffing firms that upgraded their infrastructure.", "h3": "Proven ROI", "p1": "See exactly how our custom ATS and CRM solutions impact the bottom line.", "quote": "The numbers speak for themselves.", "term_header": "ROI_CALC", "term_lines": "[METRIC] Placements up 40%.<br>[METRIC] Tech debt reduced 100%.<br>"
    }
]

def replace_nav_and_footer(filepath):
    if not os.path.exists(filepath):
        print("Not found:", filepath)
        return
    with open(filepath, 'r') as f:
        content = f.read()

    # Regex to replace nav
    nav_pattern = re.compile(r'<!-- Mega-Menu Navigation -->.*?</nav>', re.DOTALL)
    content = nav_pattern.sub(nav_replacement, content)
    
    # Regex for footer
    if '<!-- Exhaustive NinjaOne Style Footer -->' in content:
        footer_pattern = re.compile(r'<!-- Exhaustive NinjaOne Style Footer -->.*?</footer>', re.DOTALL)
        content = footer_pattern.sub(footer_replacement, content)

    with open(filepath, 'w') as f:
        f.write(content)
    print("Updated:", filepath)


os.chdir('/Users/jmartin/Documents/GitHub/transform-io')

# 1. Update index.html
existing = ['index.html']
for e in existing:
    replace_nav_and_footer(e)

# 2. Write new files
for page in pages_to_create:
    html = page_template % {
        "title": page["title"],
        "nav": nav_replacement,
        "tag": page["tag"],
        "h1": page["h1"],
        "desc": page["desc"],
        "h3": page["h3"],
        "p1": page["p1"],
        "quote": page["quote"],
        "term_header": page["term_header"],
        "term_lines": page["term_lines"],
        "footer": footer_replacement
    }
    with open(page["filename"], 'w') as f:
        f.write(html)
    print("Created:", page["filename"])
