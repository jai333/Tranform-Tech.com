import re

with open('/Users/jmartin/Documents/GitHub/ATS-CRM-Protingent/app_track/tracking_app/templates/tracking_app/home.html', 'r') as f:
    content = f.read()

# 1. Add CSS
css_to_add = """
.sc-blue { background: rgba(59,130,246,0.1) !important; color: #3b82f6 !important; }
.btn-showcase-blue { background: linear-gradient(135deg, #2563eb, #3b82f6) !important; box-shadow: 0 4px 20px rgba(59,130,246,0.3) !important; }
.btn-showcase-blue:hover { box-shadow: 0 8px 32px rgba(59,130,246,0.5) !important; }
.showcase-frame-blue { border-color: rgba(59,130,246,0.15); box-shadow: 0 24px 80px rgba(0,0,0,0.7), 0 0 60px rgba(59,130,246,0.1); }
.sf-glow-blue { background: linear-gradient(to bottom, transparent 50%, rgba(59,130,246,0.05) 100%); }

.sc-red { background: rgba(239,68,68,0.1) !important; color: #ef4444 !important; }
.btn-showcase-red { background: linear-gradient(135deg, #dc2626, #ef4444) !important; box-shadow: 0 4px 20px rgba(239,68,68,0.3) !important; }
.btn-showcase-red:hover { box-shadow: 0 8px 32px rgba(239,68,68,0.5) !important; }
"""

if ".sc-blue {" not in content:
    style_end_idx = content.find('</style>')
    if style_end_idx != -1:
        content = content[:style_end_idx] + css_to_add + content[style_end_idx:]

# 2. Add new showcase rows
html_to_add = """
        <!-- IT Ticketing Showcase -->
        <div class="showcase-row" data-reveal data-delay="100">
            <div class="showcase-col-text">
                <div class="label-tag label-blue" style="color: #3b82f6; border-color: rgba(59,130,246,0.25); background: rgba(59,130,246,0.06);">IT OPERATIONS</div>
                <h2 class="showcase-h2">Resolve Issues.<br>Empower Teams.</h2>
                <p class="showcase-p">Our modern IT Helpdesk manages incidents, assets, and requests. With automated SLA tracking and priority routing, your team stays productive.</p>
                <ul class="showcase-checklist">
                    <li>
                        <div class="sc-check sc-blue"><i class='bx bx-support'></i></div>
                        <div><strong>Automated Ticketing</strong><span>Smart routing based on issue category</span></div>
                    </li>
                    <li>
                        <div class="sc-check sc-blue"><i class='bx bx-time'></i></div>
                        <div><strong>SLA Tracking</strong><span>Never miss a critical deadline</span></div>
                    </li>
                    <li>
                        <div class="sc-check sc-blue"><i class='bx bx-bar-chart-alt-2'></i></div>
                        <div><strong>Performance Metrics</strong><span>Analyze resolution times and workload</span></div>
                    </li>
                </ul>
                <a href="{% url 'it-helpdesk-list' %}" class="btn-showcase btn-showcase-blue">Open IT Helpdesk →</a>
            </div>
            <div class="showcase-col-visual">
                <div class="showcase-frame showcase-frame-blue">
                    <img src="{% static 'tracking_app/assets/dashboard_mockup_1776111945145.png' %}" alt="IT Helpdesk Dashboard" class="showcase-img">
                    <div class="sf-glow sf-glow-blue"></div>
                    <div class="sf-badge sf-badge-top">
                        <i class='bx bx-check-circle' style="color:#3b82f6;"></i>
                        <span>100% SLA Met</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Cybersecurity Showcase (reversed) -->
        <div class="showcase-row showcase-reverse" data-reveal data-delay="100">
            <div class="showcase-col-text">
                <div class="label-tag label-red">ENTERPRISE SECURITY</div>
                <h2 class="showcase-h2">Security Is the Foundation,<br>Not a Feature.</h2>
                <p class="showcase-p">Every service we deliver is built on military-grade infrastructure. SOC2, HIPAA-ready, AES-256 encryption, zero-trust identity, and real-time threat monitoring come standard.</p>
                <ul class="showcase-checklist">
                    <li>
                        <div class="sc-check sc-red"><i class='bx bx-shield-quarter'></i></div>
                        <div><strong>SOC2 & HIPAA Ready</strong><span>Compliant from day one</span></div>
                    </li>
                    <li>
                        <div class="sc-check sc-red"><i class='bx bx-radar'></i></div>
                        <div><strong>Zero-Trust Architecture</strong><span>Strict access control globally</span></div>
                    </li>
                    <li>
                        <div class="sc-check sc-red"><i class='bx bx-bug-alt'></i></div>
                        <div><strong>Real-Time Threat Monitoring</strong><span>Detect and contain incidents instantly</span></div>
                    </li>
                </ul>
                <a href="{% url 'threat-dashboard' %}" class="btn-showcase btn-showcase-red">Access SOC Dashboard →</a>
            </div>
            <div class="showcase-col-visual">
                <div class="showcase-frame showcase-frame-red">
                    <img src="{% static 'tracking_app/assets/cybersec_mockup_1776112528216.png' %}" alt="Security Dashboard" class="showcase-img">
                    <div class="sf-glow sf-glow-red"></div>
                    <div class="sf-badge sf-badge-bottom">
                        <i class='bx bx-lock-alt' style="color:#ef4444;"></i>
                        <span>AES-256 Encrypted</span>
                    </div>
                </div>
            </div>
        </div>
"""

# Insert right before the end of showcase-section container
# Pattern to match:
#             </div>
#         </div>
#     </div>
# </section>
# 
# <!-- ═══════════════════════════════════════════════════════════
#      SCROLLING MARQUEE

target_pattern = r'(\s*</div>\s*</div>\s*</div>\s*</section>\s*<!-- ═══════════════════════════════════════════════════════════\s*SCROLLING MARQUEE)'

if "IT Ticketing Showcase" not in content:
    content = re.sub(target_pattern, lambda m: html_to_add + m.group(1), content)

# 3. Remove old Enterprise Security section
security_section_pattern = r'<!-- ═══════════════════════════════════════════════════════════\s*SECURITY \+ COMPLIANCE\s*═══════════════════════════════════════════════════════════ -->\s*<section class="section-dark">.*?</section>'
content = re.sub(security_section_pattern, '', content, flags=re.DOTALL)

with open('/Users/jmartin/Documents/GitHub/ATS-CRM-Protingent/app_track/tracking_app/templates/tracking_app/home.html', 'w') as f:
    f.write(content)

print("Modified home.html successfully.")
