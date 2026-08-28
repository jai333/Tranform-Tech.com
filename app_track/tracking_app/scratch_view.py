
@login_required
def sales_buying_radar(request):
    """
    Exotic AI Feature: Live 'Buying Signal' Radar
    Simulates real-time scanning of LinkedIn/News for target companies and drafts emails.
    """
    if not request.user.can_view_sales and not request.user.is_superuser:
        raise PermissionDenied("You do not have access to the Sales module.")

    context = {
        'page_title': 'Buying Signal Radar | Sales Intelligence',
    }
    return render(request, 'tracking_app/sales/buying_signal_radar.html', context)
