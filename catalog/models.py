from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.JSONField(default=dict)
    description = models.JSONField(default=dict)
    active = models.BooleanField(default=True)

class Product(models.Model):
    category = models.ForeignKey(Category,on_delete=models.PROTECT,related_name='products')
    name = models.JSONField(default=dict)
    description = models.JSONField(default=dict)
    care = models.JSONField(default=dict)
    image = models.ImageField(upload_to='products/%Y/%m/',blank=True)
    demo_asset = models.CharField(max_length=200,blank=True)
    color = models.CharField(max_length=30)
    occasion = models.CharField(max_length=30)
    flower_type = models.CharField(max_length=30,default='roses')
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

class Variant(models.Model):
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name='variants')
    name = models.JSONField(default=dict)
    price = models.DecimalField(max_digits=12,decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(price__gte=0),name='positive_price'),models.CheckConstraint(condition=models.Q(stock__gte=0),name='positive_stock')]

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user','product'],name='unique_favorite')]
