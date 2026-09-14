from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

class User(AbstractUser):
    username = models.CharField(max_length=254,unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    language = models.CharField(max_length=2, choices=[('uz','Uzbek'),('en','English'),('ru','Russian')], default='uz')
    theme = models.CharField(max_length=5, choices=[('light','Light'),('dark','Dark')], default='light')
    avatar = models.ImageField(upload_to='avatars/%Y/%m/', blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'),name='unique_email_ci')]

class Address(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name='addresses')
    label = models.CharField(max_length=60)
    recipient = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=500)
    is_default = models.BooleanField(default=False)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user'],condition=models.Q(is_default=True),name='one_default_address')]
