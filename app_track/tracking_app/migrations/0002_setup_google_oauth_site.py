"""
Data migration: 
  1. Sets the Django Site domain to transform-tech.com
  2. Creates (or updates) the Google SocialApp from env vars GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
  3. Links the SocialApp to Site ID 1
"""
from django.db import migrations
import os


def setup_google_oauth(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    SocialApp = apps.get_model('socialaccount', 'SocialApp')

    # Fix the site domain
    site, _ = Site.objects.get_or_create(id=1, defaults={'domain': 'transform-tech.com', 'name': 'Transform-Tech'})
    site.domain = 'transform-tech.com'
    site.name = 'Transform-Tech'
    site.save()

    client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')

    if not client_id:
        # Skip if not configured yet — admin can add later
        return

    app, created = SocialApp.objects.get_or_create(
        provider='google',
        defaults={
            'name': 'Google',
            'client_id': client_id,
            'secret': client_secret,
        }
    )
    if not created:
        app.client_id = client_id
        app.secret = client_secret
        app.save()

    app.sites.set([site])


def reverse_setup(apps, schema_editor):
    pass  # Non-destructive — leave data in place on reverse


class Migration(migrations.Migration):

    dependencies = [
        ('tracking_app', '0001_initial'),
        ('sites', '0002_alter_domain_unique'),
        ('socialaccount', '0006_alter_socialaccount_extra_data'),
    ]

    operations = [
        migrations.RunPython(setup_google_oauth, reverse_setup),
    ]
