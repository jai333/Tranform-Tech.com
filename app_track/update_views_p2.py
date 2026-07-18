import re

with open('tracking_app/views.py', 'r') as f:
    content = f.read()

# 1. Update imports
if 'ITAsset' not in content:
    content = content.replace(
        "from .models import Application, Interview, InterviewScorecard, Note, ScheduledReport",
        "from .models import Application, Interview, InterviewScorecard, Note, ScheduledReport, ITAsset"
    )
    if 'ITAsset' not in content: # fallback
        content = content.replace("from tracking_app.models import ", "from tracking_app.models import ITAsset, ")
        
# 2. Update it_helpdesk_list context
if "'active_assets': ITAsset.objects.filter(" not in content:
    content = content.replace(
        "'category_choices': ITTicket.CATEGORY_CHOICES,",
        "'category_choices': ITTicket.CATEGORY_CHOICES,\n        'active_assets': ITAsset.objects.exclude(status='retired'),"
    )

# 3. Update it_ticket_create
old_create = """        attachment = request.FILES.get('attachment')
        if title and description:
            ticket = ITTicket.objects.create(
                title=title,
                description=description,
                priority=priority,
                category=category,
                tags=tags or None,
                attachment=attachment,
                submitted_by=request.user,
            )"""

new_create = """        attachment = request.FILES.get('attachment')
        asset_id = request.POST.get('asset_id')
        
        if title and description:
            ticket = ITTicket.objects.create(
                title=title,
                description=description,
                priority=priority,
                category=category,
                tags=tags or None,
                attachment=attachment,
                submitted_by=request.user,
                asset_id=asset_id if asset_id else None,
            )"""

if old_create in content:
    content = content.replace(old_create, new_create)
else:
    print("Warning: Could not find old_create block.")

# 4. Add the it_asset_detail view at the end
asset_view = """
@login_required
def it_asset_detail(request, pk):
    asset = get_object_or_404(ITAsset, pk=pk)
    context = {
        'asset': asset,
        'tickets': asset.tickets.all().order_by('-created_at'),
        'page_title': f'Asset: {asset.asset_tag}',
    }
    return render(request, 'tracking_app/it_asset_detail.html', context)
"""

if "def it_asset_detail" not in content:
    content += asset_view

with open('tracking_app/views.py', 'w') as f:
    f.write(content)

print("Views updated successfully.")
