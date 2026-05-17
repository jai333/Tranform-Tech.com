import os
import re

templates_dir = '/Users/jmartin/Documents/GitHub/ATS-CRM-Protingent/app_track/tracking_app/templates/tracking_app'

content_map = {
    'public_blog.html': """
    <section class="container mt-xl mb-xl">
        <h3 class="text-white text-2xl mb-lg text-center">Latest Intelligence</h3>
        <div class="grid-3">
            <div class="data-card border-glow" style="padding: 0; overflow: hidden;">
                <img src="https://images.unsplash.com/photo-1488590528505-98d2b5aba04b?auto=format&fit=crop&q=80&w=800" alt="Tech Recruitment" style="width: 100%; height: 180px; object-fit: cover; filter: brightness(0.85);">
                <div style="padding: 24px;">
                    <p class="font-mono text-xs text-primary mb-sm">April 12, 2026</p>
                    <h4 class="text-white text-lg mb-sm">State of AI in Recruitment</h4>
                    <p class="text-gray mb-md" style="font-size:0.9rem;">Stop losing placements to manual workflows. How automation bridges the gap between sourcing and submission.</p>
                    <a href="#" class="text-primary font-mono text-sm">Read Article -></a>
                </div>
            </div>
            <div class="data-card border-glow" style="padding: 0; overflow: hidden;">
                <img src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&q=80&w=800" alt="Data Analytics" style="width: 100%; height: 180px; object-fit: cover; filter: brightness(0.85);">
                <div style="padding: 24px;">
                    <p class="font-mono text-xs text-primary mb-sm">March 28, 2026</p>
                    <h4 class="text-white text-lg mb-sm">Zero Trust Talent Pipelines</h4>
                    <p class="text-gray mb-md" style="font-size:0.9rem;">Transforming your service agency into a scalable system with built-in data dashboards.</p>
                    <a href="#" class="text-primary font-mono text-sm">Read Article -></a>
                </div>
            </div>
            <div class="data-card border-glow" style="padding: 0; overflow: hidden;">
                <img src="https://images.unsplash.com/photo-1542744173-8e7e53415bb0?auto=format&fit=crop&q=80&w=800" alt="Business Meeting" style="width: 100%; height: 180px; object-fit: cover; filter: brightness(0.85);">
                <div style="padding: 24px;">
                    <p class="font-mono text-xs text-primary mb-sm">March 15, 2026</p>
                    <h4 class="text-white text-lg mb-sm">ATS vs CRM Convergence</h4>
                    <p class="text-gray mb-md" style="font-size:0.9rem;">Why buying separate software for client relationships and candidate tracking is obsolete.</p>
                    <a href="#" class="text-primary font-mono text-sm">Read Article -></a>
                </div>
            </div>
        </div>
    </section>
    """,
    'public_ats.html': """
    <section class="container mt-xl mb-xl">
        <div class="grid-2 align-center mb-lg">
            <div>
                <h3 class="text-white text-2xl mb-md">Never Lose a Great Candidate</h3>
                <p class="text-gray mb-md line-height-relaxed" style="font-size: 1.1rem;">
                    Stop losing placements to manual workflows. Our Custom ATS infrastructure provides real-time pipeline visibility for US-based staffing firms, connecting sourcing directly to client submissions.
                </p>
                <ul class="feature-list mt-md">
                    <li><i class='bx bx-check-circle text-primary'></i> Drag-and-drop Kanban hiring boards.</li>
                    <li><i class='bx bx-check-circle text-primary'></i> Automated interview scheduling APIs.</li>
                    <li><i class='bx bx-check-circle text-primary'></i> 1-Click candidate submittals to hiring managers.</li>
                </ul>
            </div>
            <div class="bento-image-wrapper border-glow" style="height: 350px;">
                <img src="{% static 'tracking_app/assets/ats_dashboard.png' %}" alt="ATS Dashboard" style="filter: brightness(0.9);">
            </div>
        </div>
    </section>
    """,
    'public_crm.html': """
    <section class="container mt-xl mb-xl">
        <div class="grid-2 align-center mb-lg">
            <div>
                <h3 class="text-white text-2xl mb-md">Manage Client Pipelines</h3>
                <p class="text-gray mb-md line-height-relaxed" style="font-size: 1.1rem;">
                    Your business runs on closed deals. We build custom CRM pipelines for recruiters, allowing you to track job orders and client requirements without disjointed spreadsheets.
                </p>
                <ul class="feature-list mt-md">
                    <li><i class='bx bx-check-circle text-primary'></i> Automated workflow triggers for recruiting processes.</li>
                    <li><i class='bx bx-check-circle text-primary'></i> High switching-cost system design.</li>
                    <li><i class='bx bx-check-circle text-primary'></i> Free workflow audit to identify process bottlenecks.</li>
                </ul>
            </div>
            <div class="bento-image-wrapper border-glow" style="height: 350px;">
                <img src="{% static 'tracking_app/assets/crm_dashboard.png' %}" alt="CRM Deals" style="filter: brightness(0.9);">
            </div>
        </div>
    </section>
    """,
    'public_ai.html': """
    <section class="container mt-xl mb-xl">
        <div class="grid-2 align-center mb-lg">
            <div>
                <h3 class="text-white text-2xl mb-md">Deep Matching Technology</h3>
                <p class="text-gray mb-md line-height-relaxed" style="font-size: 1.1rem;">
                    Eliminate bias and keyword stuffing. Our NLP engine actually "reads" candidate history and constructs a 0-100 compatibility matrix by plotting experience dimensions against your exact job description.
                </p>
            </div>
            <div class="grid-2">
                <div class="data-card border-glow" style="padding: 24px;">
                    <i class='bx bx-abacus text-primary' style="font-size: 2rem;"></i>
                    <h4 class="text-white mt-sm">Cosine Similarity</h4>
                    <p class="text-gray text-xs mt-sm">Calculates conceptual distance between job reqs and resume text.</p>
                </div>
                <div class="data-card border-glow" style="padding: 24px;">
                    <i class='bx bx-search-alt-2 text-primary' style="font-size: 2rem;"></i>
                    <h4 class="text-white mt-sm">Semantic Extraction</h4>
                    <p class="text-gray text-xs mt-sm">Parses nested skills missing from standard keyword filters.</p>
                </div>
            </div>
        </div>
    </section>
    """
}

# Generic fallback
fallback_html = """
    <section class="container mt-xl mb-xl">
        <div class="grid-2 align-center mb-lg">
            <div>
                <h3 class="text-white text-2xl mb-md">Automation-Driven Recruitment</h3>
                <p class="text-gray mb-md line-height-relaxed" style="font-size: 1.1rem;">
                    Built exclusively for US tech staffing firms. We don't just sell software; we provide custom systems, SOP-driven execution, and retainers to optimize your recruitment workflow.
                </p>
                <div class="highlight-box">
                    <p class="font-mono text-white text-sm">Increase placement efficiency and reduce inefficiencies by systemizing your entire recruitment infrastructure.</p>
                </div>
            </div>
            <div class="bento-image-wrapper border-glow" style="height: 350px;">
                <img src="{% static 'tracking_app/assets/analytics_dashboard.png' %}" alt="Enterprise Software" style="filter: brightness(0.9);">
            </div>
        </div>
    </section>
"""

# Iterate over all files
for file in os.listdir(templates_dir):
    if file.endswith('.html') and file != 'home.html' and file != 'base.html':
        filepath = os.path.join(templates_dir, file)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        html_to_inject = content_map.get(file, fallback_html)

        new_content = re.sub(
            r'<section class="container mt-xl mb-xl">.*?</section>',
            html_to_inject,
            content,
            flags=re.DOTALL
        )

        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Refilled content in: {file}")
