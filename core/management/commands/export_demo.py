from django.core.management import call_command
from django.core.management.base import BaseCommand
from pathlib import Path
from django.conf import settings
class Command(BaseCommand):
    help='Export translated catalog and guide fixtures.'
    def handle(self,*args,**opts):
        p=settings.BASE_DIR/'fixtures'/'demo_catalog.json';p.parent.mkdir(exist_ok=True)
        with p.open('w',encoding='utf-8') as out: call_command('dumpdata','catalog.Category','catalog.Product','catalog.Variant','core.GuideConfig',indent=2,stdout=out)
        self.stdout.write(str(p))

