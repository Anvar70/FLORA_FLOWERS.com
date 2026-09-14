import os
from django.core.management.base import BaseCommand
from accounts.models import User

class Command(BaseCommand):
    help = 'Create or update the configured Flora administrator.'

    def handle(self, *args, **options):
        email = os.environ.get('FLORA_ADMIN_EMAIL', 'admin@flora.uz').lower()
        password = os.environ.get('FLORA_ADMIN_PASSWORD', 'FloraAdmin-2026!')
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User(username=email, email=email, first_name='Flora Admin')
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f'Administrator ready: {email}'))
