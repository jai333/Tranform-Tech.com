import re

with open('tracking_app/templates/tracking_app/candidate_gmaps_scraper.html', 'r') as f:
    content = f.read()

# Replace endpoint URLs
content = content.replace('/api/sales/gmaps/scrape/', '/candidates/api/map-scrape/')
content = content.replace('/api/sales/gmaps/import/', '/candidates/api/map-import/')

# Replace Titles and Texts
content = content.replace('Google Maps Lead Scraper', 'Google Maps Candidate Sourcing')
content = content.replace('Google Maps AI Lead Scraper', 'AI Candidate Sourcing Engine')
content = content.replace('Search Google Maps', 'Search Web Candidates')
content = content.replace('ready to scrape', 'Ready to source candidates')
content = content.replace('find highly-rated leads', 'find top-tier candidates')
content = content.replace('Import to Leads Pipeline', 'Import to Candidate Pipeline')
content = content.replace('Import Selected', 'Import Selected')

# Update Filters HTML
filter_html = """
                <!-- Keyword -->
                <div class="gm-fg">
                    <label>Job Title / Keyword</label>
                    <div style="position:relative;">
                        <i class="bx bx-search" style="position:absolute;left:12px;top:10px;color:var(--text-gray);"></i>
                        <input type="text" id="gm-keyword" class="gm-fi" placeholder="e.g. Software Engineer..." style="padding-left:34px;">
                    </div>
                </div>

                <!-- Location -->
                <div class="gm-fg">
                    <label>Target Location</label>
                    <div style="position:relative;">
                        <i class="bx bxs-map-pin" style="position:absolute;left:12px;top:10px;color:var(--text-gray);"></i>
                        <input type="text" id="gm-location" class="gm-fi" placeholder="e.g. Seattle, WA" style="padding-left:34px;">
                    </div>
                </div>

                <!-- Skills -->
                <div class="gm-fg">
                    <label>Required Skills (comma separated)</label>
                    <div style="position:relative;">
                        <i class="bx bx-code-alt" style="position:absolute;left:12px;top:10px;color:var(--text-gray);"></i>
                        <input type="text" id="gm-category" class="gm-fi" placeholder="e.g. Python, React, AWS" style="padding-left:34px;">
                    </div>
                </div>
"""

# Replace the filters section (rough regex to catch the block from keyword to category)
content = re.sub(r'<!-- Keyword -->.*?<div class="gm-fg">\s*<div style="display:flex', filter_html + '\n                <div class="gm-fg">\n                    <div style="display:flex', content, flags=re.DOTALL)

# Update Javascript renderResults to handle Candidate data
new_render_results = """
        const init = (b.name||'?').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase();
        return `
        <div class="lc" id="c${i}" onclick="tog(${i})">
            <div class="lc-chk"><i class="bx bx-check"></i></div>
            <div class="lc-av">${esc(init)}</div>
            <div class="lc-name">${esc(b.name)}</div>
            ${b.title?`<div class="lc-cat">${esc(b.title)}</div>`:''}
            <div class="lc-meta" style="margin-top:8px;">
                ${b.location ?`<div class="lc-row"><i class="bx bx-map-pin"></i>${esc(b.location)}</div>`:''}
                ${b.company ?`<div class="lc-row"><i class="bx bx-building"></i>${esc(b.company)}</div>`:''}
            </div>
            ${b.skills ? `<div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:8px;">
                ${b.skills.map(s => `<span style="background:rgba(0,229,255,0.1);color:var(--primary);font-size:0.65rem;padding:2px 6px;border-radius:4px;">${esc(s)}</span>`).join('')}
            </div>` : ''}
            <div class="lc-meta" style="margin-top:8px; border-top:1px solid rgba(255,255,255,0.1); padding-top:6px;">
                ${b.linkedin ?`<div class="lc-row"><i class="bx bxl-linkedin"></i><a href="${esc(b.linkedin)}" onclick="event.stopPropagation()" target="_blank">LinkedIn Profile</a></div>`:''}
            </div>
        </div>`;
"""
content = re.sub(r'const init = \(b\.name\|\|\'\?\'\).*?</div>`;', new_render_results, content, flags=re.DOTALL)

# Update the map marker popup
content = content.replace("`<b style=\"color:black;\">${esc(b.name)}</b><br><span style=\"color:black;\">${esc(b.category||'')}</span>`", "`<b style=\"color:black;\">${esc(b.name)}</b><br><span style=\"color:black;\">${esc(b.title||'')}</span>`")

# The payload to import: we change 'businesses' to 'candidates'
content = content.replace("businesses: Array.from(selected).map(i=>results[i]),", "candidates: Array.from(selected).map(i=>results[i]),")

# Remove checks for `serp_key_set` blocking UI
content = content.replace('{% if not serp_key_set %}disabled{% endif %}', '')
content = re.sub(r'\{% if not serp_key_set %\}.*?\{% endif %\}', '', content, flags=re.DOTALL)

with open('tracking_app/templates/tracking_app/candidate_gmaps_scraper.html', 'w') as f:
    f.write(content)
