from getpass import getpass
from django.core.management.base import BaseCommand,CommandError
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from accounts.models import User
class Command(BaseCommand):
    help='Create a trusted administrator. Password is read securely, never passed as an argument.'
    def add_arguments(self,p): p.add_argument('--email',required=True); p.add_argument('--name',default='Shop administrator')
    def handle(self,*args,**o):
        email=o['email'].lower()
        try: validate_email(email)
        except ValidationError: raise CommandError('Invalid email')
        if User.objects.filter(email__iexact=email).exists(): raise CommandError('Account already exists; do not elevate public accounts implicitly.')
        u=User(username=email,email=email,first_name=o['name'],is_staff=True,is_superuser=True)
        pw=getpass('New administrator password: ')
        if pw!=getpass('Repeat password: '): raise CommandError('Passwords do not match')
        try: validate_password(pw,u)
        except ValidationError as e: raise CommandError('; '.join(e.messages))
        u.set_password(pw);u.save()
        self.stdout.write(self.style.SUCCESS('Administrator created. Sign in at /auth/?role=admin'))

