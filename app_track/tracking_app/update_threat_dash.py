import re

with open('templates/tracking_app/threat_dashboard.html', 'r') as f:
    content = f.read()

# Add CSS for map and top IPs
css_to_add = """
.threat-grid { display: grid; grid-template-columns: 1fr 350px; gap: 1.5rem; margin-bottom: 2rem; }
@media (max-width: 1000px) { .threat-grid { grid-template-columns: 1fr; } }
.map-panel { background: var(--apple-card-bg); border: 1px solid var(--apple-border); border-radius: 12px; padding: 1.5rem; position: relative; overflow: hidden; min-height: 250px; display: flex; flex-direction: column; justify-content: space-between;}
.map-bg { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-image: radial-gradient(circle at 50% 50%, rgba(255,59,48,0.05) 0%, transparent 60%), linear-gradient(0deg, transparent 24%, rgba(0, 229, 255, 0.03) 25%, rgba(0, 229, 255, 0.03) 26%, transparent 27%, transparent 74%, rgba(0, 229, 255, 0.03) 75%, rgba(0, 229, 255, 0.03) 76%, transparent 77%, transparent), linear-gradient(90deg, transparent 24%, rgba(0, 229, 255, 0.03) 25%, rgba(0, 229, 255, 0.03) 26%, transparent 27%, transparent 74%, rgba(0, 229, 255, 0.03) 75%, rgba(0, 229, 255, 0.03) 76%, transparent 77%, transparent); background-size: 100% 100%, 30px 30px, 30px 30px; opacity: 0.8; z-index: 0; }
.map-point { position: absolute; width: 8px; height: 8px; background: var(--cyber-red); border-radius: 50%; box-shadow: 0 0 10px var(--cyber-red); z-index: 2; }
.map-point::after { content: ''; position: absolute; top: -6px; left: -6px; right: -6px; bottom: -6px; border: 1px solid var(--cyber-red); border-radius: 50%; animation: pulse-ring 2s infinite; opacity: 0.5; }
.top-ips-panel { background: var(--apple-card-bg); border: 1px solid var(--apple-border); border-radius: 12px; padding: 1.25rem; }
.ip-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--apple-border-subtle); font-size: 0.85rem; }
.ip-row:last-child { border-bottom: none; }
.ip-addr { font-family: 'Fira Code', monospace; color: var(--apple-text); }
.ip-count { color: var(--cyber-red); font-weight: 600; }
"""

if ".threat-grid {" not in content:
    content = content.replace("</style>", css_to_add + "</style>")

# Replace stats-bar with threat-grid containing map, stats-bar, and top IPs
stats_bar_target = """        <!-- Stats -->
        <div class="stats-bar">
            <div class="stat-card critical">
                <div class="stat-val">{{ stats.critical }}</div>
                <div class="stat-label"><i class="bx bx-error"></i> Critical Active</div>
            </div>
            <div class="stat-card high">
                <div class="stat-val">{{ stats.high }}</div>
                <div class="stat-label"><i class="bx bx-error-circle"></i> High Active</div>
            </div>
            <div class="stat-card open">
                <div class="stat-val">{{ stats.open }}</div>
                <div class="stat-label"><i class="bx bx-radio-circle-marked"></i> Open</div>
            </div>
            <div class="stat-card investigating">
                <div class="stat-val">{{ stats.investigating }}</div>
                <div class="stat-label"><i class="bx bx-search-alt"></i> Investigating</div>
            </div>
            <div class="stat-card total">
                <div class="stat-val">{{ stats.total }}</div>
                <div class="stat-label"><i class="bx bx-list-ul"></i> All Time</div>
            </div>
        </div>"""

stats_bar_replace = """        <!-- Threat Dashboard Overview -->
        <div class="threat-grid">
            <div class="map-panel">
                <div class="map-bg"></div>
                <div style="position: relative; z-index: 1;">
                    <div style="font-size: 0.85rem; font-weight: 700; color: var(--apple-text-secondary); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 1rem;"><i class="bx bx-world"></i> Live Threat Origin Map</div>
                    <div style="color: var(--apple-text); font-size: 1.8rem; font-weight: 300;">Avg CVSS: <strong style="color: var(--cyber-red);">{{ stats.avg_cvss }}</strong></div>
                </div>
                
                <!-- Simulated map points for visual effect -->
                <div class="map-point" style="top: 30%; left: 20%; animation-delay: 0s;"></div>
                <div class="map-point" style="top: 55%; left: 75%; animation-delay: 0.5s;"></div>
                <div class="map-point" style="top: 40%; left: 50%; animation-delay: 1.2s;"></div>
                
                <div style="position: relative; z-index: 1; margin-top: auto; font-family: 'Fira Code', monospace; font-size: 0.75rem; color: var(--cyber-red);">> SCANNING GLOBAL VECTORS...</div>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 1.5rem;">
                <!-- Stats mini-grid -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div class="stat-card critical" style="padding: 0.75rem 1rem;">
                        <div class="stat-val" style="font-size: 1.5rem;">{{ stats.critical }}</div>
                        <div class="stat-label">Critical</div>
                    </div>
                    <div class="stat-card high" style="padding: 0.75rem 1rem;">
                        <div class="stat-val" style="font-size: 1.5rem;">{{ stats.high }}</div>
                        <div class="stat-label">High</div>
                    </div>
                    <div class="stat-card open" style="padding: 0.75rem 1rem;">
                        <div class="stat-val" style="font-size: 1.5rem;">{{ stats.open }}</div>
                        <div class="stat-label">Open</div>
                    </div>
                    <div class="stat-card total" style="padding: 0.75rem 1rem;">
                        <div class="stat-val" style="font-size: 1.5rem;">{{ stats.total }}</div>
                        <div class="stat-label">Total</div>
                    </div>
                </div>
                
                <div class="top-ips-panel">
                    <div style="font-size: 0.75rem; font-weight: 700; color: var(--apple-text-secondary); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 10px;">Top Source IPs</div>
                    {% if stats.top_ips %}
                        {% for ip in stats.top_ips %}
                        <div class="ip-row">
                            <span class="ip-addr">{{ ip.source_ip }}</span>
                            <span class="ip-count">{{ ip.n }} hits</span>
                        </div>
                        {% endfor %}
                    {% else %}
                        <div style="font-size: 0.8rem; color: var(--apple-text-muted); padding: 10px 0; text-align: center;">No IPs detected</div>
                    {% endif %}
                </div>
            </div>
        </div>"""

if "threat-grid" not in content:
    content = content.replace(stats_bar_target, stats_bar_replace)


with open('templates/tracking_app/threat_dashboard.html', 'w') as f:
    f.write(content)

print("Updated threat_dashboard.html")
