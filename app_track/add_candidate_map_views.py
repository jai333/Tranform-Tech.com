import re

with open('tracking_app/views.py', 'r') as f:
    content = f.read()

new_views = """
@login_required
@require_ats_access
def candidate_gmaps_scraper(request):
    \"\"\"Renders the Google Maps Candidate Sourcing UI.\"\"\"
    return render(request, 'tracking_app/candidate_gmaps_scraper.html', {
        'page_title': 'Candidate Maps Scraper',
        'serp_key_set': True,
    })

import random
import requests
import json

@login_required
@require_ats_access
def api_candidate_gmaps_scrape(request):
    \"\"\"Searches for candidates and assigns them synthetic map coordinates based on location.\"\"\"
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
        
    try:
        body = json.loads(request.body)
    except Exception:
        body = request.POST

    keyword = (body.get('keyword') or 'Software Engineer').strip()
    location = (body.get('location') or 'San Francisco').strip()
    category = (body.get('category') or '').strip()
    skills = [s.strip() for s in category.split(',') if s.strip()] if category else []
    
    from tracking_app.services.sourcing_engine import SourcingEngine
    
    candidates = SourcingEngine.source_candidates(
        title=keyword,
        skills=skills,
        location=location,
        num_results=15
    )
    
    # Geocode the location to get a base lat/lng
    base_lat, base_lng = 37.7749, -122.4194 # default SF
    try:
        resp = requests.get(f"https://nominatim.openstreetmap.org/search?q={location}&format=json&limit=1", headers={'User-Agent': 'ATS-CRM-App'})
        if resp.status_code == 200:
            data = resp.json()
            if data:
                base_lat = float(data[0]['lat'])
                base_lng = float(data[0]['lon'])
    except Exception as e:
        print(f"Geocoding error: {e}")
        
    # Assign synthetic coordinates
    results = []
    for cand in candidates:
        lat = base_lat + random.uniform(-0.06, 0.06)
        lng = base_lng + random.uniform(-0.06, 0.06)
        results.append({
            'name': cand.get('name', 'Unknown'),
            'title': cand.get('title', keyword),
            'location': cand.get('location', location),
            'company': cand.get('company', 'Unknown'),
            'skills': cand.get('skills', skills),
            'linkedin': cand.get('linkedin', ''),
            'lat': lat,
            'lng': lng
        })
        
    return JsonResponse({'results': results, 'count': len(results)})

@login_required
@require_ats_access
def api_candidate_gmaps_import(request):
    \"\"\"Imports selected candidates from the map into the ATS.\"\"\"
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
        
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    candidates = body.get('candidates', [])
    tenant = getattr(request.user, 'tenant', None)
    
    imported = 0
    skipped = 0
    
    for c in candidates:
        name = c.get('name', '').strip()
        if not name:
            skipped += 1
            continue
            
        parts = name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''
        
        email = c.get('email', '')
        if not email:
            slug = name.lower().replace(' ', '.')
            email = f"{slug}@sourced.local"
            
        # Check duplicate
        if Candidate.objects.filter(email=email).exists():
            skipped += 1
            continue
            
        resume_text = f"Sourced via Map Scraper\\nTitle: {c.get('title')}\\nCompany: {c.get('company')}\\nLocation: {c.get('location')}\\nSkills: {', '.join(c.get('skills', []))}\\nLinkedIn: {c.get('linkedin')}"
        
        cand = Candidate.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            resume=resume_text,
            user=request.user,
            tenant=tenant
        )
        imported += 1
        
    return JsonResponse({
        'status': 'success',
        'imported': imported,
        'skipped': skipped
    })

"""

with open('tracking_app/views.py', 'a') as f:
    f.write('\n' + new_views)
