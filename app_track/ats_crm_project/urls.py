"""
URL configuration for ats_crm_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.views.generic import TemplateView

# ── Custom error handlers ────────────────────────────────────────────────────
handler404 = 'tracking_app.views.error_404'
handler500 = 'tracking_app.views.error_500'
handler403 = 'tracking_app.views.error_403'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tracking_app.urls')),
    path('video/', include('video.urls')),
    # ── SEO / crawlers ───────────────────────────────────────────────────────
    path('robots.txt', lambda r: HttpResponse(
        "User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /api/\nDisallow: /billing/\nSitemap: https://www.transform-tech.com/sitemap.xml",
        content_type="text/plain"
    )),
    path('sitemap.xml', TemplateView.as_view(
        template_name='sitemap.xml',
        content_type='application/xml'
    )),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
