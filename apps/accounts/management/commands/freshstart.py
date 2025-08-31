# apps/users/management/commands/freshstart.py

import os
import glob
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Deletes the SQLite database and all migration files for a fresh start.'

    def handle(self, *args, **options):
        # Ask User to allow this act.
        self.stdout.write(self.style.WARNING(
            'WARNING: This command will permanently delete the database file '
            'and all migration files in your custom apps.'
        ))
        confirmation = input('Are you sure you want to continue? [y/N] ')

        if confirmation.lower() != 'y':
            self.stdout.write(self.style.ERROR('Operation cancelled.'))
            return

        # --- Delete database files if any ---
        db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
        if os.path.exists(db_path):
            os.remove(db_path)
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted database file: {db_path}'))
        else:
            self.stdout.write(self.style.NOTICE(f'Database file not found at: {db_path}'))

        # ---Delete migration files (exclude init files) ---
        apps_dir = os.path.join(settings.BASE_DIR, 'apps')
        migration_files_found = False

        # Search in all dirs in apps folder 
        for app_name in os.listdir(apps_dir):
            app_path = os.path.join(apps_dir, app_name)
            if os.path.isdir(app_path):
                migrations_path = os.path.join(app_path, 'migrations')
                if os.path.isdir(migrations_path):
                    # find all python files exclude __init__.py
                    files = glob.glob(os.path.join(migrations_path, '*.py'))
                    for file_path in files:
                        if not os.path.basename(file_path) == '__init__.py':
                            os.remove(file_path)
                            migration_files_found = True
                            self.stdout.write(f'Deleted migration: {os.path.relpath(file_path, settings.BASE_DIR)}')
        
        if migration_files_found:
            self.stdout.write(self.style.SUCCESS('Successfully deleted all migration files.'))
        else:
            self.stdout.write(self.style.NOTICE('No migration files found to delete.'))

        self.stdout.write(self.style.SUCCESS('\nProject is ready for a fresh start. Now run:'))
        self.stdout.write(self.style.HTTP_INFO('First: Ensure Drop & Create Databse if useing Postgres.'))
        self.stdout.write(self.style.HTTP_INFO('1. python manage.py makemigrations'))
        self.stdout.write(self.style.HTTP_INFO('2. python manage.py migrate'))
        self.stdout.write(self.style.HTTP_INFO('3. python manage.py createsuperuser'))
