import json
from django.http import JsonResponse
from django.db.models import Q

def kb_search_api(request):
    query = request.GET.get('q', '')
    if len(query) < 3:
        return JsonResponse({'articles': []})
        
    articles = KBArticle.objects.filter(
        Q(title__icontains=query) | Q(tags__icontains=query)
    )[:5]
    
    data = [{'id': a.id, 'title': a.title, 'preview': a.content[:100]} for a in articles]
    return JsonResponse({'articles': data})

@login_required
def submit_csat(request, ticket_id):
    ticket = get_object_or_404(ITTicket, pk=ticket_id)
    if ticket.submitted_by != request.user:
        raise PermissionDenied("You can only rate your own tickets.")
        
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '')
    
    if rating:
        TicketSurvey.objects.update_or_create(
            ticket=ticket,
            defaults={'rating': rating, 'comment': comment}
        )
        # Add comment confirming survey
        ITTicketComment.objects.create(
            ticket=ticket,
            author=request.user,
            body=f"✅ User submitted CSAT rating: {rating}/5. {comment}"
        )
        
    return redirect('it-ticket-detail', pk=ticket.id)
