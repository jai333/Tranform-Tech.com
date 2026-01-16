#!/usr/bin/env python3
"""
Database reset script for the ATS/CRM application.
This script will:
1. Delete the existing SQLite database
2. Remove migration files (except __init__.py)
3. Recreate and apply migrations
4. Optionally create a superuser
5. Optionally recreate test job data

Usage: python reset_db.py [--with-data]
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

# Parse command line arguments
parser = argparse.ArgumentParser(description='Reset the database and optionally recreate test data')
parser.add_argument('--with-data', action='store_true', help='Recreate test data after reset')
args = parser.parse_args()

# Project root is the directory containing this script
PROJECT_ROOT = Path(__file__).resolve().parent

# Database file path
DB_FILE = PROJECT_ROOT / 'db.sqlite3'

# Apps with migrations
APPS = ['tracking_app', 'video']

# Colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

def print_status(message, color=GREEN):
    """Print a colored status message"""
    print(f"{color}[*] {message}{RESET}")

def print_error(message):
    """Print an error message"""
    print(f"{RED}[!] Error: {message}{RESET}")

def run_command(command, error_message=None):
    """Run a shell command and handle errors"""
    try:
        result = subprocess.run(command, check=True, shell=True, 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        if error_message:
            print_error(f"{error_message}: {e}")
            print(f"Command output: {e.stderr}")
        else:
            print_error(f"Command failed: {e}")
            print(f"Command output: {e.stderr}")
        sys.exit(1)

def delete_database():
    """Delete the SQLite database file if it exists"""
    if DB_FILE.exists():
        print_status("Deleting existing database...")
        DB_FILE.unlink()
    else:
        print_status("No existing database found.", YELLOW)

def delete_migrations():
    """Delete migration files except __init__.py"""
    print_status("Removing migration files...")
    
    for app in APPS:
        migrations_dir = PROJECT_ROOT / app / 'migrations'
        
        if not migrations_dir.exists():
            print_status(f"No migrations directory found for {app}.", YELLOW)
            continue
            
        for migration_file in migrations_dir.glob('*.py'):
            if migration_file.name != '__init__.py':
                print(f"Removing {migration_file.relative_to(PROJECT_ROOT)}")
                migration_file.unlink()
                
        # Also remove compiled Python files
        for pyc_file in migrations_dir.glob('*.pyc'):
            pyc_file.unlink()
            
        # Remove __pycache__ directory if it exists
        pycache_dir = migrations_dir / '__pycache__'
        if pycache_dir.exists():
            shutil.rmtree(pycache_dir)

def create_migrations():
    """Create new migrations"""
    print_status("Creating new migrations...")
    
    for app in APPS:
        print(f"Creating migrations for {app}...")
        run_command(f"python manage.py makemigrations {app}", 
                   f"Failed to create migrations for {app}")

def apply_migrations():
    """Apply migrations to create the database schema"""
    print_status("Applying migrations...")
    run_command("python manage.py migrate", "Failed to apply migrations")

def create_superuser():
    """Create a superuser for the application"""
    print_status("Creating superuser...")
    
    try:
        # Create a superuser non-interactively
        os.environ['DJANGO_SUPERUSER_USERNAME'] = 'admin'
        os.environ['DJANGO_SUPERUSER_EMAIL'] = 'admin@example.com'
        os.environ['DJANGO_SUPERUSER_PASSWORD'] = 'admin'  # Insecure, for development only
        
        run_command("python manage.py createsuperuser --noinput",
                  "Failed to create superuser")
        
        print_status("Superuser created with username 'admin' and password 'admin'")
    
    except Exception as e:
        print_error(f"Failed to create superuser: {e}")
        print_status("You can create a superuser manually with: python manage.py createsuperuser", YELLOW)

def create_recruiter_user():
    """Create a recruiter user for the application"""
    print_status("Creating recruiter user...")
    
    try:
        # Use Django shell to create the recruiter user
        recruiter_creation_script = """
from tracking_app.models import User
from django.contrib.auth.hashers import make_password

# Recruiter user details
username = 'recruiter'
password = 'bTiN!*Yk1GQij14y'
email = 'recruiter1@example.com'

# Check if user already exists
if not User.objects.filter(username=username).exists():
    # Create the recruiter user
    user = User.objects.create(
        username=username,
        email=email,
        password=make_password(password),
        first_name='Recruiter',
        last_name='One',
        role='recruiter',
        is_staff=True
    )
    print(f"Recruiter user created with username '{username}'")
else:
    print(f"Recruiter user '{username}' already exists")
"""
        
        # Write the script to a temporary file
        temp_script_path = PROJECT_ROOT / 'temp_create_recruiter.py'
        with open(temp_script_path, 'w') as f:
            f.write(recruiter_creation_script)
        
        # Run the script with Django shell
        run_command(f"python manage.py shell < {temp_script_path}", 
                   "Failed to create recruiter user")
        
        # Delete the temporary script
        if temp_script_path.exists():
            temp_script_path.unlink()
        
        print_status("Recruiter user created with username 'recruiter1' and password 'bTiN!*Yk1GQij14y'")
    
    except Exception as e:
        print_error(f"Failed to create recruiter user: {e}")

def create_test_data():
    """Create test data using the create_jobs.py script"""
    if args.with_data:
        print_status("Creating test data...")
        
        create_jobs_path = PROJECT_ROOT / 'create_jobs.py'
        if not create_jobs_path.exists():
            print_error("create_jobs.py script not found")
            return
            
        run_command("python manage.py shell < create_jobs.py",
                   "Failed to create test data")
    else:
        print_status("Skipping test data creation. Use --with-data flag to create test data.", YELLOW)

def main():
    """Main function to reset the database"""
    print_status("Starting database reset...", YELLOW)
    
    # Check if we're in a Django project
    if not (PROJECT_ROOT / 'manage.py').exists():
        print_error("This script must be run from the root of a Django project")
        sys.exit(1)
    
    # Make sure the virtual environment is activated
    try:
        import django
    except ImportError:
        print_error("Django not found. Make sure the virtual environment is activated.")
        print_status("Try: source .venv/bin/activate", YELLOW)
        sys.exit(1)
    
    # Perform reset steps
    delete_database()
    delete_migrations()
    create_migrations()
    apply_migrations()
    create_superuser()
    create_recruiter_user()
    create_test_data()
    
    print_status("Database reset complete!", GREEN)
    print_status("You can now run the development server with: python manage.py runserver", GREEN)
    print_status("Admin login: username 'admin', password 'admin'", GREEN)
    print_status("Recruiter login: username 'recruiter', password 'bTiN!*Yk1GQij14y'", GREEN)

if __name__ == "__main__":
    main() 