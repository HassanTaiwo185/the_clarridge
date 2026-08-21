from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from users.models import Profile
from datetime import date
import os


class Command(BaseCommand):
    help = "Creates a default superuser if one doesn't already exist"

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("Superuser already exists, skipping.")
            return

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not all([username, email, password]):
            self.stderr.write("Missing DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD env vars.")
            return

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )

        Profile.objects.get_or_create(
            user=user,
            defaults={"phone_number": "0000000000", "date_of_birth": date(2000, 1, 1)},
        )

        self.stdout.write(f"Superuser '{email}' created with profile.")