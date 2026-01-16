#!/usr/bin/env python3
"""Generate simple static HTML previews for the site (homepage + jobs list)
This script reads the `Job` model and writes `preview_generated_home.html` and
`preview_generated_jobs.html` in the current folder.
Run from `app_track` with the project's venv Python.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_crm_project.settings')
django.setup()

from tracking_app.models import Job, User
from django.utils.html import escape

def render_home(jobs):
    jobs_html = ''
    for job in jobs[:10]:
        jobs_html += f"<li><a href=\"/jobs/{job.id}/\">{escape(job.title)}</a> — {escape(job.location or '')}</li>\n"

    return f"""
<html>
<head><meta charset='utf-8'><title>Preview - Home</title></head>
<body>
<h1>Site Preview — Home</h1>
<p>Showing up to 10 jobs from the database.</p>
<ul>
{jobs_html}
</ul>
</body>
</html>
"""

def render_jobs(jobs):
    rows = ''
    for job in jobs:
        rows += f"<article><h2>{escape(job.title)}</h2><p><strong>Company:</strong> {escape(job.company or '')}</p><p>{escape(job.description or '')[:400]}</p><p><strong>Location:</strong> {escape(job.location or '')}</p><hr></article>\n"

    return f"""
<html>
<head><meta charset='utf-8'><title>Preview - Jobs</title></head>
<body>
<h1>Site Preview — Jobs</h1>
{rows}
</body>
</html>
"""

if __name__ == '__main__':
    jobs = list(Job.objects.all().order_by('-id'))
    home_html = render_home(jobs)
    jobs_html = render_jobs(jobs)

    with open('preview_generated_home.html', 'w', encoding='utf-8') as f:
        f.write(home_html)
    with open('preview_generated_jobs.html', 'w', encoding='utf-8') as f:
        f.write(jobs_html)

    print(f"Wrote preview_generated_home.html ({len(jobs[:10])} entries) and preview_generated_jobs.html ({len(jobs)} entries)")
