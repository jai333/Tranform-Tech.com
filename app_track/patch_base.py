
with open('/Users/jmartin/Documents/GitHub/ATS-CRM-Protingent/app_track/tracking_app/templates/tracking_app/base.html', 'r') as f:
    content = f.read()

modal_html = """
<!-- Cmd+K Global Search Modal -->
<div class="modal fade" id="globalSearchModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-lg modal-dialog-centered">
    <div class="modal-content" style="background: var(--apple-bg); border: 1px solid var(--apple-border); border-radius: 12px; overflow: hidden;">
      <div class="modal-header" style="border-bottom: 1px solid rgba(255,255,255,0.1); padding: 1rem 1.5rem;">
        <i class="fa-solid fa-magnifying-glass" style="color: var(--apple-text-secondary); margin-right: 12px;"></i>
        <input type="text" id="globalSearchInput" class="form-control" style="background: transparent; border: none; color: white; font-size: 1.2rem; box-shadow: none; padding: 0;" placeholder="Search Leads, Candidates, Tickets..." autocomplete="off">
        <span class="badge bg-dark" style="font-size: 0.7rem; border: 1px solid var(--apple-border);">ESC</span>
      </div>
      <div class="modal-body p-0" style="max-height: 400px; overflow-y: auto;" id="globalSearchResults">
        <div style="padding: 2rem; text-align: center; color: var(--apple-text-secondary);">
          Start typing to search across all workspaces...
        </div>
      </div>
    </div>
  </div>
</div>

<script>
// Cmd+K to open search
document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        var searchModal = new bootstrap.Modal(document.getElementById('globalSearchModal'));
        searchModal.show();
    }
});

document.getElementById('globalSearchModal').addEventListener('shown.bs.modal', function () {
    document.getElementById('globalSearchInput').focus();
});

let debounceTimer;
document.getElementById('globalSearchInput').addEventListener('input', function(e) {
    clearTimeout(debounceTimer);
    const query = e.target.value.trim();
    const resultsContainer = document.getElementById('globalSearchResults');
    
    if (query.length < 2) {
        resultsContainer.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--apple-text-secondary);">Start typing to search...</div>';
        return;
    }
    
    debounceTimer = setTimeout(() => {
        resultsContainer.innerHTML = '<div style="padding: 2rem; text-align: center; color: #00E5FF;"><i class="fa-solid fa-circle-notch fa-spin"></i> Searching...</div>';
        
        fetch('/api/v1/search/?q=' + encodeURIComponent(query))
            .then(res => res.json())
            .then(data => {
                if (!data.results || data.results.length === 0) {
                    resultsContainer.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--apple-text-secondary);">No results found.</div>';
                    return;
                }
                
                let html = '<div class="list-group list-group-flush">';
                data.results.forEach(item => {
                    let icon = 'fa-file';
                    let color = '#fff';
                    if (item.type === 'Lead') { icon = 'fa-user'; color = '#10b981'; }
                    if (item.type === 'Deal') { icon = 'fa-dollar-sign'; color = '#10b981'; }
                    if (item.type === 'Candidate') { icon = 'fa-id-badge'; color = '#ec4899'; }
                    if (item.type === 'IT Ticket') { icon = 'fa-ticket'; color = '#6366f1'; }
                    
                    html += '<a href="' + item.url + '" class="list-group-item list-group-item-action d-flex align-items-center gap-3" style="background: transparent; border-bottom: 1px solid rgba(255,255,255,0.05); padding: 1rem 1.5rem; color: white;">' +
                            '<div style="width: 32px; height: 32px; border-radius: 8px; background: rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center;">' +
                                '<i class="fa-solid ' + icon + '" style="color: ' + color + ';"></i>' +
                            '</div>' +
                            '<div>' +
                                '<div style="font-weight: 600; font-size: 0.95rem;">' + item.title + '</div>' +
                                '<div style="font-size: 0.8rem; color: var(--apple-text-secondary);">' + item.type + ' • ' + item.subtitle + '</div>' +
                            '</div>' +
                        '</a>';
                });
                html += '</div>';
                resultsContainer.innerHTML = html;
            });
    }, 300);
});
</script>
"""

if 'id="globalSearchModal"' not in content:
    content = content.replace('</body>', modal_html + '\n</body>')
    with open('/Users/jmartin/Documents/GitHub/ATS-CRM-Protingent/app_track/tracking_app/templates/tracking_app/base.html', 'w') as f:
        f.write(content)
    print('Injected Cmd+K search into base.html')
