"""
Management command: python manage.py create_initial_director

Creates the first director account from environment variables.
Safe for production — idempotent, no demo data, strong password required.

Environment variables:
    INITIAL_DIRECTOR_USERNAME  — login for the director account
    INITIAL_DIRECTOR_PASSWORD  — password (min 8 characters)
    INITIAL_DIRECTOR_NAME      — optional full name, e.g. "Фируз Рахимов"
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class Command(BaseCommand):
    help = 'Create the initial director account from env vars (production-safe, idempotent)'

    def handle(self, *args, **kwargs):
        from apps.accounts.models import CustomUser

        if CustomUser.objects.filter(role=CustomUser.ROLE_DIRECTOR).exists():
            self.stdout.write('Director already exists — nothing to do.')
            return

        username = os.getenv('INITIAL_DIRECTOR_USERNAME', '').strip()
        password = os.getenv('INITIAL_DIRECTOR_PASSWORD', '').strip()

        if not username or not password:
            self.stdout.write(self.style.WARNING(
                'No director exists and INITIAL_DIRECTOR_USERNAME / '
                'INITIAL_DIRECTOR_PASSWORD are not set.\n'
                'Set these environment variables to create the first director, '
                'or run `python manage.py seed_data` in development.'
            ))
            return

        try:
            validate_password(password)
        except ValidationError as exc:
            self.stderr.write(self.style.ERROR(
                'INITIAL_DIRECTOR_PASSWORD is too weak: ' + '; '.join(exc.messages)
            ))
            return

        full_name = os.getenv('INITIAL_DIRECTOR_NAME', '').strip()
        first_name, _, last_name = full_name.partition(' ')

        user = CustomUser.objects.create_user(
            username=username,
            password=password,
            role=CustomUser.ROLE_DIRECTOR,
            first_name=first_name,
            last_name=last_name,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Director account "{user.username}" created.'
        ))
