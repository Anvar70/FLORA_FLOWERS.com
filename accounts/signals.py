from django.db.models.signals import pre_save,post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import User
@receiver(pre_save,sender=User)
def replaced_avatar(sender,instance,**kwargs):
    if not instance.pk: return
    old=sender.objects.filter(pk=instance.pk).first()
    if old and old.avatar and old.avatar.name!=getattr(instance.avatar,'name',''):
        storage,name=old.avatar.storage,old.avatar.name
        transaction.on_commit(lambda:storage.delete(name))
@receiver(post_delete,sender=User)
def deleted_avatar(sender,instance,**kwargs):
    if instance.avatar:
        storage,name=instance.avatar.storage,instance.avatar.name
        transaction.on_commit(lambda:storage.delete(name))

