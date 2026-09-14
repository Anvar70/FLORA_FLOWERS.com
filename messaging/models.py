from django.db import models
from django.conf import settings

class Conversation(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='conversations')
    product = models.ForeignKey('catalog.Product',null=True,blank=True,on_delete=models.SET_NULL)
    order = models.ForeignKey('orders.Order',null=True,blank=True,on_delete=models.SET_NULL)
    subject = models.CharField(max_length=150)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-updated']

class Message(models.Model):
    conversation = models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL)
    seller = models.BooleanField(default=False)
    body = models.CharField(max_length=2000)
    read = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['created']

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='notifications')
    order = models.ForeignKey('orders.Order',on_delete=models.CASCADE)
    kind = models.CharField(max_length=30)
    status = models.CharField(max_length=20,blank=True)
    read = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created']
