import re

with open('tracking_app/views.py', 'r') as f:
    content = f.read()

# 1. Update it_helpdesk_list
old_helpdesk_list = """    base_qs = ITTicket.objects.select_related('submitted_by', 'assigned_to').prefetch_related('comments')
    if not (request.user.is_staff or request.user.is_admin_role):
        base_qs = base_qs.filter(submitted_by=request.user)"""
new_helpdesk_list = """    base_qs = ITTicket.objects.select_related('submitted_by', 'assigned_to').prefetch_related('comments')
    if request.user.is_it_enduser:
        base_qs = base_qs.filter(submitted_by=request.user)"""
content = content.replace(old_helpdesk_list, new_helpdesk_list)

# 2. Update it_ticket_detail context and permissions
old_ticket_detail = """@login_required
def it_ticket_detail(request, pk):
    \"\"\"Detail view for a single IT ticket with comment thread.\"\"\"
    ticket = get_object_or_404(ITTicket, pk=pk)

    if request.method == 'POST':"""
    
new_ticket_detail = """from django.core.exceptions import PermissionDenied

@login_required
def it_ticket_detail(request, pk):
    \"\"\"Detail view for a single IT ticket with comment thread.\"\"\"
    ticket = get_object_or_404(ITTicket, pk=pk)
    
    # End Users can only view their own tickets
    if request.user.is_it_enduser and ticket.submitted_by != request.user:
        raise PermissionDenied("You do not have permission to view this ticket.")

    if request.method == 'POST':"""
content = content.replace(old_ticket_detail, new_ticket_detail)

old_comments = """    comments = ticket.comments.select_related('author').all()"""
new_comments = """    comments = ticket.comments.select_related('author').all()
    if request.user.is_it_enduser:
        comments = comments.exclude(is_internal=True)"""
content = content.replace(old_comments, new_comments)

# 3. Add it_admin_settings view at the end
admin_view = """
@login_required
def it_admin_settings(request):
    if not request.user.is_it_admin:
        raise PermissionDenied("Only IT Administrators can access this page.")
        
    slas = SLAConfiguration.objects.all().order_by('priority')
    
    context = {
        'slas': slas,
        'page_title': 'IT Admin Settings',
    }
    return render(request, 'tracking_app/it_admin_settings.html', context)
"""
if "def it_admin_settings" not in content:
    content += admin_view

with open('tracking_app/views.py', 'w') as f:
    f.write(content)

print("Views updated successfully.")
