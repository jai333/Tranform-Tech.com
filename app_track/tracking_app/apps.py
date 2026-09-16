from django.apps import AppConfig


class TrackingAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tracking_app'

    def ready(self):
        import tracking_app.signals
        self._sync_google_oauth()

    def _sync_google_oauth(self):
        """
        If SOCIALACCOUNT_PROVIDERS has an 'APP' config for Google in settings,
        remove any DB-based SocialApp records for Google to avoid
        allauth's MultipleObjectsReturned error.
        """
        try:
            from django.conf import settings
            google_cfg = settings.SOCIALACCOUNT_PROVIDERS.get('google', {})
            app_cfg = google_cfg.get('APP', {})
            if not app_cfg.get('client_id'):
                return  # No settings config, leave DB records alone

            from allauth.socialaccount.models import SocialApp
            deleted, _ = SocialApp.objects.filter(provider='google').delete()
            if deleted:
                import logging
                logging.getLogger(__name__).info(
                    'OAuth: removed %d Google SocialApp DB record(s) — '
                    'using settings.SOCIALACCOUNT_PROVIDERS APP config instead.', deleted
                )
        except Exception:
            pass  # Never block startup
