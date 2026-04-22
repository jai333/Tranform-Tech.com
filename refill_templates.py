import os
import re

templates_dir = '/Users/jmartin/Documents/GitHub/ATS-CRM-Protingent/app_track/tracking_app/templates/tracking_app'

content_map = {
    'public_blog.html': """
    <section class="container mt-xl mb-xl">
        <h3 class="text-white text-2xl mb-lg text-center">Latest Intelligence</h3>
        <div class="grid-3">
            <div class="data-card border-glow" style="padding: 24px;">
                <p class="font-mono text-xs text-primary mb-sm">April 12, 2026</p>
                <h4 class="text-white text-lg mb-sm">State of AI in Recruitment</h4>
                <p class="text-gray mb-md" style="font-size:0.9rem;">How large language models and cosine similarity engines are replacing boolean searches entirely.</p>
                <a href="#" class="text-primary font-mono text-sm">Read Article -></a>
            </div>
            <div class="data-card border-glow" style="padding: 24px;">
                <p class="font-mono text-xs text-primary mb-sm">March 28, 2026</p>
                <h4 class="text-white text-lg mb-sm">Zero Trust Talent Pipelines</h4>
                <p class="text-gray mb-md" style="font-size:0.9rem;">Protecting candidate data records with ZTNA while maintaining speed-to-market.</p>
                <a href="#" class="text-primary font-mono text-sm">Read Article -></a>
            </div>
            <div class="data-card border-glow" style="padding: 24px;">
                <p class="font-mono text-xs text-primary mb-sm">March 15, 2026</p>
                <h4 class="text-white text-lg mb-sm">ATS vs CRM Convergence</h4>
                <p class="text-gray mb-md" style="font-size:0.9rem;">Why buying separate software for client relationships and candidate tracking is obsolete.</p>
                <a href="#" class="text-primary font-mono text-sm">Read Article -></a>
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
                    Stop manually shifting resumes across local folders. Our unified ATS pipeline provides real-time visibility into your talent pool, automatically sequencing emails and tracking interviews.
                </p>
                <ul class="feature-list mt-md">
                    <li><i class='bx bx-check-circle text-primary'></i> Drag-and-drop Kanban hiring boards.</li>
                    <li><i class='bx bx-check-circle text-primary'></i> Automated interview scheduling APIs.</li>
                    <li><i class='bx bx-check-circle text-primary'></i> 1-Click candidate submittals to hiring managers.</li>
                </ul>
            </div>
            <div class="bento-image-wrapper border-glow" style="height: 350px;">
                <img src="https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&q=80&w=800" alt="ATS Dashboard" style="filter: brightness(0.9);">
            </div>
        </div>
    </section>
    """,
    'public_crm.html': """
    <section class="container mt-xl mb-xl">
        <div class="grid-2 align-center mb-lg">
            <div>
                <h3 class="text-white text-2xl mb-md">Manage Client Requisitions</h3>
                <p class="text-gray mb-md line-height-relaxed" style="font-size: 1.1rem;">
                    Your business runs on closed deals. Natively track client fees, job orders, and split placements without ever leaving the candidate network. Syncs natively with billing ledgers.
                </p>
                <ul class="feature-list mt-md">
                    <li><i class='bx bx-check-circle text-primary'></i> Real-time pipeline forecasting.</li>
                    <li><i class='bx bx-check-circle text-primary'></i> Automated outreach to cold corporate contacts.</li>
                    <li><i class='bx bx-check-circle text-primary'></i> Client-specific portal access for live review.</li>
                </ul>
            </div>
            <div class="bento-image-wrapper border-glow" style="height: 350px;">
                <img src="https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&q=80&w=800" alt="CRM Deals" style="filter: brightness(0.9);">
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
                <h3 class="text-white text-2xl mb-md">Enterprise-Grade Infrastructure</h3>
                <p class="text-gray mb-md line-height-relaxed" style="font-size: 1.1rem;">
                    Deployed securely on sovereign clouds. Transform.io connects high-speed recruitment operations directly with reliable, automated IT workflows, eliminating middleware bottlenecks.
                </p>
                <div class="highlight-box">
                    <p class="font-mono text-white text-sm">Trusted by top agencies to reduce operational drag by up to 60% within the first quarter of deployment.</p>
                </div>
            </div>
            <div class="bento-image-wrapper border-glow" style="height: 350px;">
                <img src="https://images.unsplash.com/photo-1600880292203-757bb62b4baf?auto=format&fit=crop&q=80&w=800" alt="Enterprise Software" style="filter: brightness(0.9);">
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
