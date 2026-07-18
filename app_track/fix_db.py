from django.db import connection
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ats_crm_project.settings")
import django
django.setup()

tables_to_drop = [
    'tracking_app_automationrun',
    'tracking_app_itticketcomment',
    'tracking_app_ticketauditlog',
    'tracking_app_ticketworklog',
    'tracking_app_itticket',
    'tracking_app_itasset',
    'tracking_app_itvendor',
    'tracking_app_kbarticle',
    'tracking_app_routingrule',
    'tracking_app_slaconfiguration',
    'tracking_app_scheduledreport',
    'tracking_app_threatincident',
    'tracking_app_ticketmacro',
    'tracking_app_ticketsurvey',
    'tracking_app_devprojectrequest'
]

with connection.cursor() as cursor:
    cursor.execute("PRAGMA foreign_keys = OFF;")
    for table in tables_to_drop:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"Dropped {table}")
    
    # Remove migrations 0003 and above from django_migrations
    cursor.execute("DELETE FROM django_migrations WHERE app='tracking_app' AND name >= '0003'")
    print("Cleared django_migrations")
    cursor.execute("PRAGMA foreign_keys = ON;")
