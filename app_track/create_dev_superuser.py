#!/usr/bin/env python3
"""
Create a development superuser if one doesn't exist.
Run from the project `app_track` folder using the project's python:
  & '<venv>/Scripts/python.exe' create_dev_superuser.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ats_crm_project.settings')
django.setup()

from django.contrib.auth import get_user_model

def create_superuser(username='devadmin', email='devadmin@example.com', password='DevAdm1n!2025'):
    User = get_user_model()
    if User.objects.filter(username=username).exists():
        print(f"Superuser already exists: {username}")
        return False

    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Created superuser: {username} / {password}")
    return True

if __name__ == '__main__':
    create_superuser()
