from django.db import models
from django.conf import settings

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='cart')

class CartItem(models.Model):
    cart = models.ForeignKey(Cart,on_delete=models.CASCADE,related_name='items')
    variant = models.ForeignKey('catalog.Variant',on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(default=1)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['cart','variant'],name='unique_cart_variant'),models.CheckConstraint(condition=models.Q(quantity__gte=1,quantity__lte=99),name='cart_quantity_range')]

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name='orders')
    key = models.UUIDField(unique=True)
    recipient = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=500)
    delivery_date = models.DateField()
    slot = models.CharField(max_length=30)
    gift_message = models.CharField(max_length=500,blank=True)
    notes = models.CharField(max_length=1000,blank=True)
    subtotal = models.DecimalField(max_digits=14,decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=12,decimal_places=2)
    total = models.DecimalField(max_digits=14,decimal_places=2)
    currency = models.CharField(max_length=5)
    status = models.CharField(max_length=20,default='pending',choices=[(s,s) for s in ['pending','confirmed','preparing','out_for_delivery','delivered','cancelled']])
    payment_status = models.CharField(max_length=12,default='unpaid',choices=[('unpaid','unpaid'),('paid','paid')])
    payment_method = models.CharField(max_length=12,default='cod')
    stock_restored = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created']

class OrderItem(models.Model):
    order = models.ForeignKey(Order,on_delete=models.CASCADE,related_name='items')
    variant = models.ForeignKey('catalog.Variant',null=True,on_delete=models.SET_NULL)
    product_name = models.JSONField()
    variant_name = models.JSONField()
    unit_price = models.DecimalField(max_digits=12,decimal_places=2)
    quantity = models.PositiveSmallIntegerField()
    subtotal = models.DecimalField(max_digits=14,decimal_places=2)
