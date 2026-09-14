from django.db import models
class GuideConfig(models.Model):
    data = models.JSONField(default=dict)
    updated = models.DateTimeField(auto_now=True)
