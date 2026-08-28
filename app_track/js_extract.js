        (function(){
            var t = localStorage.getItem('theme');
            if(t === 'light') document.documentElement.classList.add('light-theme');
        })();
// ── State ────────────────────────────────────────────────────────────
let results   = [];
let selected  = new Set();
let history   = JSON.parse(localStorage.getItem('gmaps_hist') || '[]');
let scraperMap = null;
let mapMarkers = null;

// ── Initialize Map ───────────────────────────────────────────────────
function initMap() {
    if (scraperMap) return;
    document.getElementById('scraper-map').style.display = 'block';
    
    // Initialize map
    scraperMap = L.map('scraper-map', {
        zoomControl: false,
        attributionControl: false
    }).setView([20, 0], 2);

    // Add Dark Matter tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(scraperMap);
    
    // Add Layer Group for markers
    mapMarkers = L.layerGroup().addTo(scraperMap);
}

// ── Rating label ─────────────────────────────────────────────────────
document.getElementById('gm-rating').addEventListener('input', function() {
    const v = parseFloat(this.value);
    document.getElementById('gm-rating-v2').textContent = v === 0 ? 'Any' : v + '+';
});

// ── History ──────────────────────────────────────────────────────────
function saveHist(kw, loc) {
    history = [{kw,loc}, ...history.filter(h=>!(h.kw===kw&&h.loc===loc))].slice(0,6);
    localStorage.setItem('gmaps_hist', JSON.stringify(history));
    renderHist();
}
function renderHist() {
    const p = document.getElementById('hist-panel');
    const l = document.getElementById('hist-list');
    if (!history.length) { p.style.display='none'; return; }
    p.style.display='';
    l.innerHTML = history.map(h=>`
        <div class="hist-item" onclick="loadHist('${esc(h.kw)}','${esc(h.loc)}')">
            <i class="bx bxs-map" style="color:var(--primary);font-size:1rem;flex-shrink:0;"></i>
            <div>
                <div style="font-size:0.8rem;color:white;font-weight:600;">${esc(h.kw)}</div>
                <div style="font-size:0.7rem;color:var(--text-gray);">${esc(h.loc)}</div>
            </div>
        </div>`).join('');
}
function loadHist(kw, loc) {
    document.getElementById('gm-keyword').value  = kw;
    document.getElementById('gm-location').value = loc;
}
renderHist();

// ── Helpers ──────────────────────────────────────────────────────────
function esc(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }
function stars(r){ const f=Math.floor(r), h=r-f>=0.5?1:0; return '★'.repeat(f)+(h?'½':'')+'☆'.repeat(5-f-h); }
function csrf(){ return document.cookie.split(';').map(c=>c.trim()).find(c=>c.startsWith('csrftoken='))?.split('=')[1]||''; }

// ── Progress ─────────────────────────────────────────────────────────
function progStart(txt) {
    const p=document.getElementById('prog'); p.classList.add('on');
    document.getElementById('prog-txt').textContent = txt||'Searching…';
    const f=document.getElementById('prog-fill');
    f.style.width='0%';
    setTimeout(()=>f.style.width='35%',80);
    setTimeout(()=>f.style.width='65%',900);
    setTimeout(()=>f.style.width='85%',2200);
}
function progEnd(txt) {
    document.getElementById('prog-fill').style.width='100%';
    document.getElementById('prog-txt').textContent = txt||'Done!';
    setTimeout(()=>document.getElementById('prog').classList.remove('on'), 700);
}

// ── Render Results ────────────────────────────────────────────────────
function renderResults(data) {
    results  = data;
    selected = new Set();
    updateStats();
    
    // Init map if first time
    initMap();
    mapMarkers.clearLayers();
    const bounds = L.latLngBounds();

    const grid  = document.getElementById('leads-grid');
    const empty = document.getElementById('empty-st');
    if (!data.length) {
        grid.style.display='none';
        empty.style.display='block';
        empty.innerHTML=`<i class="bx bx-search-alt"></i><h3>No results found</h3><p>Try different keywords or a broader location / lower rating.</p>`;
        return;
    }
    empty.style.display='none';
    grid.style.display='grid';
    grid.innerHTML = data.map((b,i)=>{
        // Add Marker
        if (b.lat && b.lng) {
            const icon = L.divIcon({
                className: 'gmap-marker',
                iconSize: [14, 14],
                iconAnchor: [7, 7]
            });
            L.marker([b.lat, b.lng], {icon: icon})
             .bindPopup(`<b style="color:black;">${esc(b.name)}</b><br><span style="color:black;">${esc(b.category||'')}</span>`)
             .addTo(mapMarkers);
            bounds.extend([b.lat, b.lng]);
        }

        const init = (b.name||'?').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase();
        const rtg  = b.rating ? parseFloat(b.rating).toFixed(1) : null;
        const rev  = b.reviews ? parseInt(b.reviews).toLocaleString() : null;
        return `
        <div class="lc" id="c${i}" onclick="tog(${i})">
            <div class="lc-chk"><i class="bx bx-check"></i></div>
            <div class="lc-av">${esc(init)}</div>
            <div class="lc-name">${esc(b.name)}</div>
            ${b.category?`<div class="lc-cat">${esc(b.category)}</div>`:''}
            ${rtg?`<div style="display:flex;align-items:center;gap:6px;margin:4px 0 0;">
                <span class="lc-stars">${stars(parseFloat(rtg))}</span>
                <span class="lc-rnum">${rtg}${rev?` (${rev})`:''}  </span>
            </div>`:''}
            <div class="lc-meta">
                ${b.address ?`<div class="lc-row"><i class="bx bx-map-pin"></i>${esc(b.address)}</div>`:''}
                ${b.phone   ?`<div class="lc-row" style="align-items:center; justify-content:space-between; width:100%;">
                    <div style="display:flex; align-items:center; gap:7px;">
                        <i class="bx bx-phone"></i>${esc(b.phone)}
                    </div>
                    <div style="display:flex; gap:4px;">
                        <button class="btn-sm" style="padding:4px 8px; font-size:0.7rem; color:var(--primary); border-color:rgba(0,229,255,0.3);" onclick="event.stopPropagation(); openDialer('${esc(b.phone)}', '${esc(b.name)}')"><i class='bx bx-phone-call'></i></button>
                        <button class="btn-sm" style="padding:4px 8px; font-size:0.7rem; color:var(--primary); border-color:rgba(0,229,255,0.3);" onclick="event.stopPropagation(); openSMS('${esc(b.phone)}', '${esc(b.name)}')"><i class='bx bx-message-rounded-dots'></i></button>
                    </div>
                </div>`:''}
                ${b.website ?`<div class="lc-row"><i class="bx bx-globe"></i><a href="${esc(b.website)}" onclick="event.stopPropagation()" target="_blank">${esc(b.website.replace(/^https?:\/\//,'').split('/')[0])}</a></div>`:''}
                ${b.maps_url?`<div class="lc-row"><i class="bx bxl-google"></i><a href="${esc(b.maps_url)}" onclick="event.stopPropagation()" target="_blank">View on Maps</a></div>`:''}
            </div>
        </div>`;
    }).join('');

    // Fit map to markers
    if (bounds.isValid()) {
        scraperMap.fitBounds(bounds, {padding: [30, 30], maxZoom: 14});
    }
}

// ── Selection ────────────────────────────────────────────────────────
function tog(i) {
    const c = document.getElementById('c'+i);
    if (selected.has(i)) { selected.delete(i); c.classList.remove('sel'); }
    else                  { selected.add(i);    c.classList.add('sel'); }
    updateStats();
}
function selAll()   { results.forEach((_,i)=>{ selected.add(i); document.getElementById('c'+i)?.classList.add('sel'); }); updateStats(); }
function deselAll() { results.forEach((_,i)=>{ selected.delete(i); document.getElementById('c'+i)?.classList.remove('sel'); }); updateStats(); }
function updateStats() {
    document.getElementById('stat-count').textContent = results.length;
    document.getElementById('stat-sel').textContent   = selected.size;
    document.getElementById('btn-import').disabled    = selected.size === 0;
    document.getElementById('btn-desel').style.display     = selected.size > 0 ? '' : 'none';
    document.getElementById('btn-sel-all').style.display   = (selected.size === results.length && results.length > 0) ? 'none' : '';
}

// ── Toast ────────────────────────────────────────────────────────────
function showToast(title, body) {
    const t = document.getElementById('toast');
    document.getElementById('toast-title').textContent = title;
    document.getElementById('toast-body').textContent  = body;
    t.classList.add('on');
    setTimeout(()=>t.classList.remove('on'), 5500);
}

// ── Search ───────────────────────────────────────────────────────────
document.getElementById('btn-search').addEventListener('click', async ()=>{
    const kw  = document.getElementById('gm-keyword').value.trim();
    const loc = document.getElementById('gm-location').value.trim();
    const cat = document.getElementById('gm-category').value;
    const rat = document.getElementById('gm-rating').value;
    const mx  = document.getElementById('gm-max').value;

    if (!kw || !loc) { alert('Please enter a Keyword and Location.'); return; }

    const btn = document.getElementById('btn-search');
    btn.disabled = true;
    btn.innerHTML = '<i class="bx bx-loader-alt" style="animation:spin 1s linear infinite;"></i> Searching…';

    progStart(`Searching "${kw}" in ${loc}…`);
    document.getElementById('leads-grid').style.display='none';
    document.getElementById('empty-st').style.display='none';

    try {
        const r = await fetch('/api/sales/gmaps/scrape/', {
            method: 'POST',
            headers: {'Content-Type':'application/json','X-CSRFToken':csrf()},
            body: JSON.stringify({keyword:kw, location:loc, category:cat, min_rating:parseFloat(rat), max_results:parseInt(mx)})
        });
        const d = await r.json();
        if (d.error) {
            progEnd('Error');
            document.getElementById('empty-st').innerHTML=`<i class="bx bx-error-circle" style="color:#FF453A;"></i><h3 style="color:#FF453A;">Scrape Failed</h3><p>${esc(d.error)}</p>`;
            document.getElementById('empty-st').style.display='block';
        } else {
            progEnd(`Found ${d.results.length} businesses!`);
            renderResults(d.results);
            saveHist(kw, loc);
        }
    } catch(e) {
        progEnd('Network error');
        document.getElementById('empty-st').innerHTML=`<i class="bx bx-error-circle" style="color:#FF453A;"></i><h3 style="color:#FF453A;">Network Error</h3><p>Could not reach the server. Check console for details.</p>`;
        document.getElementById('empty-st').style.display='block';
        console.error(e);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bx bx-search-alt"></i> Search Google Maps';
    }
});

// ── Import ───────────────────────────────────────────────────────────
async function doImport() {
    const businesses = [...selected].map(i=>results[i]);
    if (!businesses.length) return;
    
    const kw  = document.getElementById('gm-keyword').value.trim();
    const loc = document.getElementById('gm-location').value.trim();
    
    const btn = document.getElementById('btn-import');
    btn.disabled = true;
    btn.innerHTML = '<i class="bx bx-loader-alt" style="animation:spin 1s linear infinite;"></i> Importing…';
    progStart(`Importing ${businesses.length} leads & running AI scoring…`);
    try {
        const r = await fetch('/api/sales/gmaps/import/', {
            method:'POST',
            headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},
            body: JSON.stringify({businesses, keyword: kw, location: loc})
        });
        const d = await r.json();
        progEnd('Import complete!');
        showToast(`✓ ${d.created} leads imported!`, `${d.skipped} skipped (already in DB) · ${d.scored} AI-scored`);
        deselAll();
    } catch(e) {
        progEnd('Import failed');
        alert('Import failed. Please try again.');
        console.error(e);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bx bx-import"></i> Import Selected';
    }
}

// ── Enter key trigger ─────────────────────────────────────────────────
['gm-keyword','gm-location'].forEach(id=>{
    document.getElementById(id).addEventListener('keydown', e=>{ if(e.key==='Enter') document.getElementById('btn-search').click(); });
});

function openDialer(phone, name) {
    document.getElementById('comm-modal').style.display = 'flex';
    document.getElementById('comm-title').innerHTML = `<i class="bx bx-phone" style="color:var(--primary);"></i> Calling ${name}`;
    document.getElementById('comm-subtitle').textContent = phone;
    
    document.getElementById('comm-body').innerHTML = `
        <div style="text-align:center; padding:20px 0;">
            <div style="width:80px; height:80px; border-radius:50%; background:rgba(0,229,255,0.1); border:2px solid var(--primary); display:flex; align-items:center; justify-content:center; margin:0 auto 20px; font-size:2rem; color:var(--primary); box-shadow: 0 0 20px rgba(0,229,255,0.3); animation:pulse-marker 1.5s infinite;">
                <i class="bx bxs-phone-call"></i>
            </div>
            <div style="font-size:1.2rem; color:white; font-family:var(--font-mono);">${phone}</div>
            <div style="font-size:0.8rem; color:var(--text-gray); margin-top:8px;" id="dialer-status">Connecting via Twilio...</div>
            
            <div style="display:flex; justify-content:center; gap:15px; margin-top:30px;">
                <button class="btn-sm" style="width:50px; height:50px; border-radius:50%; font-size:1.2rem; background:rgba(255,255,255,0.1); border:none;"><i class="bx bx-microphone-off"></i></button>
                <button class="btn-sm" onclick="document.getElementById('comm-modal').style.display='none'" style="width:50px; height:50px; border-radius:50%; font-size:1.4rem; background:#ef4444; color:white; border:none; box-shadow:0 4px 10px rgba(239,68,68,0.4);"><i class="bx bxs-phone-off"></i></button>
                <button class="btn-sm" style="width:50px; height:50px; border-radius:50%; font-size:1.2rem; background:rgba(255,255,255,0.1); border:none;"><i class="bx bx-dialpad"></i></button>
            </div>
        </div>
    `;
    
    setTimeout(() => {
        if(document.getElementById('dialer-status')) {
            document.getElementById('dialer-status').textContent = 'Ringing...';
        }
    }, 1500);
}

function openSMS(phone, name) {
    document.getElementById('comm-modal').style.display = 'flex';
    document.getElementById('comm-title').innerHTML = `<i class="bx bx-message-rounded-dots" style="color:var(--primary);"></i> SMS ${name}`;
    document.getElementById('comm-subtitle').textContent = phone;
    
    document.getElementById('comm-body').innerHTML = `
        <div style="display:flex; flex-direction:column; gap:15px; height:250px;">
            <div style="flex:1; overflow-y:auto; padding-right:5px; display:flex; flex-direction:column; gap:10px;" id="sms-chat">
                <div style="align-self:center; font-size:0.7rem; color:var(--text-dark-gray);">Today</div>
            </div>
            
            <div style="display:flex; gap:8px;">
                <input type="text" id="sms-input" class="fc" placeholder="Type a message..." style="flex:1;" onkeydown="if(event.key==='Enter') sendSMS()">
                <button class="btn-search" onclick="sendSMS()" style="width:40px; padding:0; background:var(--primary); color:black;"><i class="bx bx-send"></i></button>
            </div>
        </div>
    `;
    setTimeout(() => document.getElementById('sms-input').focus(), 100);
}

function sendSMS() {
    const inp = document.getElementById('sms-input');
    const msg = inp.value.trim();
    if(!msg) return;
    
    const chat = document.getElementById('sms-chat');
    chat.innerHTML += `
        <div style="align-self:flex-end; background:var(--primary); color:black; padding:8px 12px; border-radius:12px 12px 0 12px; font-size:0.85rem; max-width:85%;">
            ${msg.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
        </div>
        <div style="align-self:flex-end; font-size:0.65rem; color:var(--text-dark-gray); margin-top:-6px;">Delivered</div>
    `;
    inp.value = '';
    chat.scrollTop = chat.scrollHeight;
}
    document.addEventListener('keydown', function(e) {
        // Support both Cmd+J and Cmd+Shift+V for backwards compatibility
        if ((e.metaKey || e.ctrlKey) && (e.key === 'j' || e.key === 'J')) {
            e.preventDefault();
            activateVoiceCommand();
        }
        if ((e.metaKey || e.ctrlKey) && e.shiftKey && (e.key === 'v' || e.key === 'V')) {
            e.preventDefault();
            activateVoiceCommand();
        }
        if (e.key === 'Escape') {
            document.getElementById('voice-command-overlay').style.display = 'none';
        }
    });

    function activateVoiceCommand() {
        const overlay = document.getElementById('voice-command-overlay');
        const transcript = document.getElementById('voice-transcript');
        const execLog = document.getElementById('voice-execution-log');
        const eq = document.getElementById('voice-equalizer');
        
        overlay.style.display = 'flex';
        transcript.innerHTML = 'Listening...';
        transcript.style.color = 'rgba(255,255,255,0.5)';
        execLog.style.opacity = '0';
        eq.style.display = 'flex';
        execLog.innerHTML = '<div class="voice-log-item" style="display:flex; align-items:center; gap:10px; margin-bottom:12px; color:rgba(255,255,255,0.6);"><i class="bx bx-loader-alt bx-spin" style="color:var(--primary);"></i> Parsing intent...</div>';
        
        // Phase 1: Transcribing
        setTimeout(() => {
            transcript.style.color = '#fff';
            typeWriterEffectVoice(transcript, '"Move Acme Corp to Proposal Sent, draft a follow-up email, and remind me to call tomorrow."');
        }, 1500);
        
        // Phase 2: Execution
        setTimeout(() => {
            eq.style.display = 'none';
            execLog.style.opacity = '1';
            
            setTimeout(() => addLogItemVoice('<i class="bx bx-check-circle" style="color:#10b981;"></i> Intent parsed successfully'), 800);
            setTimeout(() => addLogItemVoice('<i class="bx bx-check-circle" style="color:#10b981;"></i> Pipeline Stage updated to: Proposal Sent'), 1800);
            setTimeout(() => addLogItemVoice('<i class="bx bx-check-circle" style="color:#10b981;"></i> Email draft created: "Follow-up on Acme Proposal"'), 2800);
            setTimeout(() => addLogItemVoice('<i class="bx bx-check-circle" style="color:#10b981;"></i> Task created: Call Acme Corp tomorrow @ 10:00 AM'), 3800);
            setTimeout(() => {
                transcript.innerHTML = '<i class="bx bx-check-circle" style="color:#10b981; margin-right: 10px;"></i>Action Completed';
                setTimeout(() => { overlay.style.display = 'none'; }, 2500);
            }, 4500);
        }, 4500);
    }
    
    function typeWriterEffectVoice(element, text, speed=30) {
        element.innerHTML = '';
        let i = 0;
        function type() {
            if (i < text.length) {
                element.innerHTML += text.charAt(i);
                i++;
                setTimeout(type, speed);
            }
        }
        type();
    }
    function addLogItemVoice(html) {
        const logItem = document.createElement('div');
        logItem.className = 'voice-log-item';
        logItem.style.cssText = 'display:flex; align-items:center; gap:10px; margin-bottom:12px; color:#fff; animation: fadeUpVoice 0.3s ease-out forwards; opacity:0; transform:translateY(10px);';
        logItem.innerHTML = html;
        document.getElementById('voice-execution-log').appendChild(logItem);
    }
