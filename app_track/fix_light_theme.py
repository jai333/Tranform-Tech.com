#!/usr/bin/env python3
"""
Fix all hardcoded dark-mode colors in HTML templates so they work
correctly in both dark and light themes using CSS variables.
"""
import os
import re

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "tracking_app", "templates", "tracking_app")

# ----- Replacement rules (regex pattern -> replacement) ----------------
# Order matters — more specific patterns first.
RULES = [
    # White text
    (r'(?<!\w)color\s*:\s*#fff(?=[;\s"\'})>])', 'color:var(--apple-text)'),
    (r'(?<!\w)color\s*:\s*#ffffff(?=[;\s"\'})>])', 'color:var(--apple-text)'),
    (r'(?<!\w)color\s*:\s*rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.9[5-9]?\s*\)', 'color:var(--apple-text)'),
    (r'(?<!\w)color\s*:\s*rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.7\s*\)', 'color:var(--apple-text-secondary)'),
    (r'(?<!\w)color\s*:\s*rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.[45]\s*\)', 'color:var(--apple-text-secondary)'),
    (r'(?<!\w)color\s*:\s*rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.[12]?\d?\s*\)', 'color:var(--apple-text-muted)'),

    # Black / near-black backgrounds
    (r'(?<!\w)background\s*:\s*#0a0a0a(?=[;\s"\'})>])', 'background:var(--apple-bg)'),
    (r'(?<!\w)background\s*:\s*#111(?=[;\s"\'})>])', 'background:var(--apple-card-bg)'),
    (r'(?<!\w)background\s*:\s*#111111(?=[;\s"\'})>])', 'background:var(--apple-card-bg)'),
    (r'(?<!\w)background\s*:\s*#1a1a1a(?=[;\s"\'})>])', 'background:var(--apple-card-bg)'),
    (r'(?<!\w)background\s*:\s*#141414(?=[;\s"\'})>])', 'background:var(--apple-card-bg)'),
    (r'(?<!\w)background\s*:\s*#0c0d12(?=[;\s"\'})>])', 'background:var(--apple-card-bg)'),
    (r'(?<!\w)background\s*:\s*#0d1f0e(?=[;\s"\'})>])', 'background:var(--apple-card-bg)'),

    # Semi-transparent white backgrounds -> row hover / subtle
    (r'(?<!\w)background\s*:\s*rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.0[1-4]\s*\)', 'background:var(--apple-bg)'),
    (r'(?<!\w)background\s*:\s*rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.0[5-9]\s*\)', 'background:var(--apple-row-hover)'),
    (r'(?<!\w)background\s*:\s*rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.1\s*\)', 'background:var(--apple-border)'),

    # Semi-transparent black backgrounds -> inputs
    (r'(?<!\w)background\s*:\s*rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\.[12]\s*\)', 'background:var(--apple-input-bg)'),
    (r'(?<!\w)background\s*:\s*rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\.[34]\s*\)', 'background:var(--apple-input-bg)'),
    (r'(?<!\w)background\s*:\s*rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\.5\s*\)', 'background:var(--apple-input-bg)'),

    # Borders
    (r'(?<!\w)border\s*:\s*1px solid rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.0[5-9]\s*\)', 'border:1px solid var(--apple-border)'),
    (r'(?<!\w)border\s*:\s*1px solid rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.1[0-5]?\s*\)', 'border:1px solid var(--apple-border)'),
    (r'(?<!\w)border\s*:\s*1px solid rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.2\s*\)', 'border:1px solid var(--apple-border)'),
    (r'(?<!\w)border-bottom\s*:\s*1px solid rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.0[5-9]\s*\)', 'border-bottom:1px solid var(--apple-border)'),
    (r'(?<!\w)border-bottom\s*:\s*1px solid rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.1\s*\)', 'border-bottom:1px solid var(--apple-border)'),
    (r'(?<!\w)border-right\s*:\s*1px solid rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.0[5-9]\s*\)', 'border-right:1px solid var(--apple-border)'),
    (r'(?<!\w)border-top\s*:\s*1px solid rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.0[5-9]\s*\)', 'border-top:1px solid var(--apple-border)'),
    (r'border-color\s*:\s*rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.1\s*\)', 'border-color:var(--apple-border)'),
    (r'(?<!\w)border\s*:\s*1px solid #2a2a2a(?=[;\s"\'})>])', 'border:1px solid var(--apple-border)'),
    (r'(?<!\w)border\s*:\s*1px solid #1e1e1e(?=[;\s"\'})>])', 'border:1px solid var(--apple-border-subtle)'),

    # Input backgrounds
    (r'(?<!\w)background\s*:\s*rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.04\s*\)', 'background:var(--apple-input-bg)'),
    (r'(?<!\w)background\s*:\s*rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0\.03\s*\)', 'background:var(--apple-input-bg)'),

    # Common page bg used in some older templates
    (r'(?<!\w)background\s*:\s*#fafafc(?=[;\s"\'})>])', 'background:var(--apple-bg)'),
    (r'(?<!\w)background\s*:\s*#fcfcfd(?=[;\s"\'})>])', 'background:var(--apple-bg)'),
    (r'(?<!\w)background\s*:\s*#eef0f5(?=[;\s"\'})>])', 'background:var(--apple-bg)'),
    (r'(?<!\w)background\s*:\s*#f8fbff(?=[;\s"\'})>])', 'background:var(--apple-bg)'),
    (r'(?<!\w)background\s*:\s*#f0f7ff(?=[;\s"\'})>])', 'background:var(--apple-bg)'),
]

# Compile all patterns once
COMPILED = [(re.compile(p, re.IGNORECASE), r) for p, r in RULES]

# Files to SKIP (public pages are intentionally styled differently)
SKIP_FILES = {"base_public.html", "lead_qualification.html", "lead_qualification_success.html", "demo_booking.html"}

total_files = 0
total_replacements = 0

for root, dirs, files in os.walk(TEMPLATE_DIR):
    # Skip venv, node_modules, etc.
    dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules")]
    for filename in files:
        if not filename.endswith(".html"):
            continue
        if filename in SKIP_FILES:
            continue

        filepath = os.path.join(root, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            original = f.read()

        modified = original
        file_replacements = 0
        for pattern, replacement in COMPILED:
            new_modified, count = pattern.subn(replacement, modified)
            if count:
                file_replacements += count
                modified = new_modified

        if modified != original:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(modified)
            print(f"  ✓ [{file_replacements:3d} fixes] {os.path.relpath(filepath, TEMPLATE_DIR)}")
            total_files += 1
            total_replacements += file_replacements

print(f"\n✅ Done! Fixed {total_replacements} color values across {total_files} template files.")
