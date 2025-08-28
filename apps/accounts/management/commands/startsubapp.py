import os
import shutil
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a Django app inside a folder (e.g., python manage.py folder_name.app_name)"

    def add_arguments(self, parser):
        parser.add_argument("dotted_name", type=str, help="Format: folder_name.app_name")

    def handle(self, *args, **options):
        dotted_name = options["dotted_name"]

        if "." not in dotted_name:
            raise CommandError("Format must be folder_name.app_name (e.g., my_apps.accounts)")

        folder, app_name = dotted_name.split(".", 1)

        # paths
        base_dir = os.getcwd()
        folder_path = os.path.join(base_dir, folder)
        target_path = os.path.join(folder_path, app_name)

        # if the apps folder does not exist, create it
        os.makedirs(folder_path, exist_ok=True)

        # first create the app
        temp_path = os.path.join(base_dir, app_name)
        if os.path.exists(temp_path):
            raise CommandError(f"Temporary path {temp_path} already exists.")

        self.stdout.write(f"📦 Creating app '{app_name}' ...")
        call_command("startapp", app_name)

        # move the app to the target path
        shutil.move(temp_path, target_path)

        self.stdout.write(self.style.SUCCESS(f"✅ App '{app_name}' created inside '{folder}/'"))
