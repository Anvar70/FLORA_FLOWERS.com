from decimal import Decimal
from uuid import uuid4
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.cache import cache
from django.db import transaction, IntegrityError
from django.db.models import Q, F, Sum, Min
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.views import exception_handler as drf_exception_handler
from accounts.models import User, Address
from catalog.models import Category, Product, Variant, Favorite
from orders.models import Cart, CartItem, Order, OrderItem
from messaging.models import Conversation, Message, Notification
from core.models import GuideConfig

def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        response.data = {'error':response.data}
    return response

def fail(code): raise ValidationError({'code':code})
def image_check(value):
    if value:
        if value.size > 5*1024*1024: fail('image_size')
        from PIL import Image
        try:
            im = Image.open(value)
            if im.format not in ['JPEG','PNG','WEBP'] or im.width*im.height > 16000000: fail('image_invalid')
            im.verify()
            value.seek(0)
        except (OSError, ValueError): fail('image_invalid')
        value.name = str(uuid4()) + '.' + {'JPEG':'jpg','PNG':'png','WEBP':'webp'}[im.format]
    return value

def translations(value):
    if not isinstance(value,dict) or not value.get('en') or any(k not in ('uz','en','ru') or not isinstance(v,str) or len(v)>5000 for k,v in value.items()):
        fail('translations_required')
    return value

class AdminOnly(permissions.BasePermission):
    def has_permission(self, request, view): return request.user.is_authenticated and request.user.is_staff
class CatalogPermission(permissions.BasePermission):
    def has_permission(self, request, view): return request.method in permissions.SAFE_METHODS or request.user.is_authenticated and request.user.is_staff

class ProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=150,allow_blank=False,required=False)
    phone = serializers.RegexField(r'^\+?[0-9 ()-]{7,30}$',allow_blank=True,required=False)
    avatar = serializers.ImageField(required=False,allow_null=True,validators=[image_check])
    class Meta:
        model=User
        fields=['id','first_name','email','phone','language','theme','avatar','is_staff']
        read_only_fields=['id','email','is_staff']

class AddressSerializer(serializers.ModelSerializer):
    phone = serializers.RegexField(r'^\+?[0-9 ()-]{7,30}$')
    class Meta:
        model=Address
        fields=['id','label','recipient','phone','address','is_default']
    def validate_phone(self,v):
        if len(v)<7: fail('phone_invalid')
        return v

class CategorySerializer(serializers.ModelSerializer):
    name=serializers.JSONField(validators=[translations])
    description=serializers.JSONField(validators=[translations])
    class Meta:
        model=Category
        fields=['id','name','description','active']

class VariantSerializer(serializers.ModelSerializer):
    name=serializers.JSONField(validators=[translations])
    class Meta:
        model=Variant
        fields=['id','product','name','price','stock','active']

class ProductSerializer(serializers.ModelSerializer):
    name=serializers.JSONField(validators=[translations])
    description=serializers.JSONField(validators=[translations])
    care=serializers.JSONField(validators=[translations])
    image=serializers.ImageField(required=False,allow_null=True,validators=[image_check])
    variants=serializers.SerializerMethodField()
    def get_variants(self,obj):
        values=list(obj.variants.all())
        request=self.context.get('request')
        params=request.query_params if request else {}
        if not request or not request.user.is_staff: values=[v for v in values if v.active]
        if params.get('available')=='true': values=[v for v in values if v.stock>0]
        for key,op in [('min_price',lambda a,b:a>=b),('max_price',lambda a,b:a<=b)]:
            if params.get(key): values=[v for v in values if op(v.price,Decimal(params[key]))]
        return VariantSerializer(values,many=True).data
    image_url=serializers.SerializerMethodField()
    category_name=serializers.JSONField(source='category.name',read_only=True)
    def get_image_url(self,obj):
        return obj.image.url if obj.image else '/static/'+(obj.demo_asset or 'images/hero.jpg')
    class Meta:
        model=Product
        fields=['id','category','category_name','name','description','care','image','image_url','color','occasion','flower_type','active','variants']

class CatalogViewSet(viewsets.ModelViewSet):
    permission_classes=[CatalogPermission]
    def perform_destroy(self, instance):
        instance.active=False
        instance.save(update_fields=['active'])

class CategoryViewSet(CatalogViewSet):
    serializer_class=CategorySerializer
    def get_queryset(self):
        return Category.objects.all().order_by('id') if self.request.user.is_staff else Category.objects.filter(active=True).order_by('id')

class ProductViewSet(CatalogViewSet):
    serializer_class=ProductSerializer
    def get_queryset(self):
        q=Product.objects.select_related('category').prefetch_related('variants').order_by('-created')
        p=self.request.query_params
        if not self.request.user.is_staff: q=q.filter(active=True,category__active=True)
        if p.get('search'):
            s=p['search'][:100]
            q=q.filter(Q(name__en__icontains=s)|Q(name__uz__icontains=s)|Q(name__ru__icontains=s))
        if p.get('category'):
            if not p['category'].isdigit(): fail('invalid_filter')
            q=q.filter(category_id=p['category'])
        for k in ['color','occasion','flower_type']:
            if p.get(k): q=q.filter(**{k:p[k]})
        vf={'variants__active':True}
        for key,lookup in [('min_price','gte'),('max_price','lte')]:
            if p.get(key):
                try:
                    amount=Decimal(p[key])
                    if not amount.is_finite() or amount<0: raise ValueError()
                except Exception: fail('invalid_filter')
                vf['variants__price__'+lookup]=amount
        if p.get('available')=='true': vf['variants__stock__gt']=0
        if not self.request.user.is_staff or len(vf)>1 or p.get('available')=='true': q=q.filter(**vf)
        q=q.annotate(min_price=Min('variants__price')).distinct()
        if p.get('favorites')=='true':
            if not self.request.user.is_authenticated: return q.none()
            q=q.filter(favorite__user=self.request.user)
        sort={'price_asc':'min_price','price_desc':'-min_price','newest':'-created'}.get(p.get('sort'),'-created')
        return q.order_by(sort,'id')
    @action(detail=True,methods=['post'],permission_classes=[permissions.IsAuthenticated])
    def favorite(self,request,pk=None):
        p=self.get_object()
        obj,created=Favorite.objects.get_or_create(user=request.user,product=p)
        if not created: obj.delete()
        return Response({'saved':created})

class VariantViewSet(viewsets.ModelViewSet):
    permission_classes=[AdminOnly]
    serializer_class=VariantSerializer
    queryset=Variant.objects.select_related('product').all().order_by('id')
    def perform_destroy(self, instance):
        instance.active=False
        instance.save(update_fields=['active'])

class AddressViewSet(viewsets.ModelViewSet):
    serializer_class=AddressSerializer
    def get_queryset(self): return Address.objects.filter(user=self.request.user).order_by('-is_default','id')
    def perform_create(self,serializer):
        with transaction.atomic():
            User.objects.select_for_update().get(pk=self.request.user.pk)
            if serializer.validated_data.get('is_default'): self.get_queryset().update(is_default=False)
            serializer.save(user=self.request.user)
    def perform_update(self,serializer):
        with transaction.atomic():
            User.objects.select_for_update().get(pk=self.request.user.pk)
            if serializer.validated_data.get('is_default'): self.get_queryset().exclude(pk=serializer.instance.pk).update(is_default=False)
            serializer.save()

@api_view(['GET','PATCH','DELETE'])
def profile(request):
    user=request.user
    if request.method=='GET': return Response(ProfileSerializer(user).data)
    if request.method=='PATCH':
        s=ProfileSerializer(user,data=request.data,partial=True); s.is_valid(raise_exception=True); s.save()
        return Response(s.data)
    if not user.check_password(request.data.get('password','')): fail('password_incorrect')
    if request.data.get('confirm') is not True: fail('confirmation_required')
    with transaction.atomic():
        admins=list(User.objects.select_for_update().filter(is_staff=True,is_active=True))
        if user.is_staff and len(admins)<=1: fail('last_admin')
        # Retain financial snapshots while removing recipient PII.
        user.orders.update(recipient='Deleted account',phone='',address='',gift_message='',notes='')
        user.delete()
    logout(request)
    return Response(status=204)

@api_view(['POST'])
def password_change(request):
    if not request.user.check_password(request.data.get('current_password','')): fail('password_incorrect')
    password=request.data.get('password','')
    try: validate_password(password,request.user)
    except DjangoValidationError: fail('password_weak')
    request.user.set_password(password); request.user.save()
    update_session_auth_hash(request,request.user)
    return Response({'ok':True})

@api_view(['POST'])
def email_change(request):
    if not request.user.check_password(request.data.get('password','')): fail('password_incorrect')
    email=serializers.EmailField().run_validation(request.data.get('email','')).lower()
    if User.objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists(): fail('email_taken')
    from django.core import signing
    from django.core.mail import send_mail
    from django.utils.translation import gettext as _
    from hashlib import sha256
    token=signing.dumps({'uid':request.user.pk,'email':email,'old_email':request.user.email,'password_digest':sha256(request.user.password.encode()).hexdigest()},salt='email-change')
    url=request.build_absolute_uri('/email-confirm/'+token+'/')
    text={'uz':'Pochta manzilini tasdiqlash','en':'Confirm your email address','ru':'Подтвердите электронную почту'}[request.user.language]
    send_mail(text,text+'\n'+url,settings.DEFAULT_FROM_EMAIL,[email])
    return Response({'ok':True,'verification_required':True})

def cart_data(user):
    cart,_=Cart.objects.get_or_create(user=user)
    rows=[]; subtotal=Decimal('0')
    for row in cart.items.select_related('variant__product__category'):
        v=row.variant; p=v.product
        amount=v.price*row.quantity; subtotal+=amount
        rows.append({'id':row.id,'variant':v.id,'name':p.name,'variant_name':v.name,'product':p.id,'image_url':p.image.url if p.image else '/static/'+(p.demo_asset or 'images/hero.jpg'),'price':str(v.price),'quantity':row.quantity,'subtotal':str(amount),'stock':v.stock,'available':p.active and p.category.active and v.active and v.stock>=row.quantity})
    fee=settings.SHOP_DELIVERY_FEE if rows else Decimal('0')
    return {'items':rows,'subtotal':str(subtotal),'delivery_fee':str(fee),'total':str(subtotal+fee),'currency':settings.SHOP_CURRENCY}

class CartInput(serializers.Serializer):
    variant=serializers.IntegerField(min_value=1)
    quantity=serializers.IntegerField(min_value=1,max_value=99)

@api_view(['GET','POST','PATCH','DELETE'])
def cart(request):
    if request.method=='GET': return Response(cart_data(request.user))
    if request.method=='DELETE':
        item_id=serializers.IntegerField(min_value=1).run_validation(request.data.get('id'))
        CartItem.objects.filter(cart__user=request.user,pk=item_id).delete()
        return Response(cart_data(request.user))
    s=CartInput(data=request.data); s.is_valid(raise_exception=True)
    with transaction.atomic():
        c,_=Cart.objects.get_or_create(user=request.user)
        Cart.objects.select_for_update().get(pk=c.pk)
        v=get_object_or_404(Variant.objects.select_related('product__category'),pk=s.validated_data['variant'])
        row=CartItem.objects.filter(cart=c,variant=v).first()
        qty=s.validated_data['quantity']+(row.quantity if row and request.method=='POST' else 0)
        if not v.active or not v.product.active or not v.product.category.active or qty>v.stock or qty>99: fail('stock_unavailable')
        CartItem.objects.update_or_create(cart=c,variant=v,defaults={'quantity':qty})
    return Response(cart_data(request.user))

class CheckoutSerializer(serializers.Serializer):
    key=serializers.UUIDField()
    recipient=serializers.CharField(max_length=120)
    phone=serializers.RegexField(r'^\+?[0-9 ()-]{7,30}$')
    address=serializers.CharField(min_length=8,max_length=500)
    delivery_date=serializers.DateField()
    slot=serializers.ChoiceField(choices=settings.DELIVERY_SLOTS)
    gift_message=serializers.CharField(max_length=500,allow_blank=True,required=False,default='')
    notes=serializers.CharField(max_length=1000,allow_blank=True,required=False,default='')
    def validate_delivery_date(self,v):
        today=timezone.localdate()
        if v<today+timedelta(days=1) or v>today+timedelta(days=30): fail('date_invalid')
        return v

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model=OrderItem
        fields=['id','product_name','variant_name','unit_price','quantity','subtotal']
class OrderSerializer(serializers.ModelSerializer):
    items=OrderItemSerializer(many=True,read_only=True)
    customer=serializers.SerializerMethodField()
    def get_customer(self,o): return o.user.first_name if o.user else 'Deleted account'
    class Meta:
        model=Order
        fields=['id','customer','recipient','phone','address','delivery_date','slot','gift_message','notes','subtotal','delivery_fee','total','currency','status','payment_status','payment_method','created','items']
        read_only_fields=fields

@api_view(['POST'])
def checkout(request):
    s=CheckoutSerializer(data=request.data); s.is_valid(raise_exception=True)
    d=dict(s.validated_data)
    with transaction.atomic():
        # Serialize all checkout operations for the same account on PostgreSQL.
        User.objects.select_for_update().get(pk=request.user.pk)
        existing=Order.objects.filter(key=d['key']).first()
        if existing:
            if existing.user_id!=request.user.pk: fail('duplicate_key')
            return Response(OrderSerializer(existing).data)
        c,_=Cart.objects.get_or_create(user=request.user)
        rows=list(c.items.select_related('variant__product__category').order_by('variant_id'))
        if not rows: fail('cart_empty')
        total=Decimal('0'); snapshots=[]
        for row in rows:
            v=Variant.objects.select_for_update().get(pk=row.variant_id); p=row.variant.product
            if not v.active or not p.active or not p.category.active or row.quantity>99: fail('stock_unavailable')
            if not Variant.objects.filter(pk=v.pk,stock__gte=row.quantity).update(stock=F('stock')-row.quantity): fail('stock_unavailable')
            amount=v.price*row.quantity; total+=amount
            snapshots.append(dict(variant=v,product_name=p.name,variant_name=v.name,unit_price=v.price,quantity=row.quantity,subtotal=amount))
        order=Order.objects.create(user=request.user,subtotal=total,delivery_fee=settings.SHOP_DELIVERY_FEE,total=total+settings.SHOP_DELIVERY_FEE,currency=settings.SHOP_CURRENCY,**d)
        OrderItem.objects.bulk_create([OrderItem(order=order,**row) for row in snapshots])
        Notification.objects.bulk_create([Notification(user=u,order=order,kind='new_order') for u in User.objects.filter(is_staff=True,is_active=True)])
        c.items.all().delete()
    return Response(OrderSerializer(order).data,status=201)

TRANSITIONS={'pending':['confirmed','cancelled'],'confirmed':['preparing','cancelled'],'preparing':['out_for_delivery','cancelled'],'out_for_delivery':['delivered'],'delivered':[],'cancelled':[]}
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=OrderSerializer
    def get_queryset(self):
        q=Order.objects.select_related('user').prefetch_related('items')
        if not self.request.user.is_staff: q=q.filter(user=self.request.user)
        if self.request.query_params.get('status'): q=q.filter(status=self.request.query_params['status'])
        search=self.request.query_params.get('search','')
        if search: q=q.filter(Q(recipient__icontains=search)|Q(id=int(search) if search.isdigit() else -1))
        return q
    @action(detail=True,methods=['post'],permission_classes=[AdminOnly])
    def transition(self,request,pk=None):
        with transaction.atomic():
            o=get_object_or_404(Order.objects.select_for_update(),pk=pk)
            target=request.data.get('status')
            if target not in TRANSITIONS[o.status]: fail('transition_invalid')
            if target=='cancelled' and not o.stock_restored:
                for row in o.items.all():
                    if row.variant_id: Variant.objects.filter(pk=row.variant_id).update(stock=F('stock')+row.quantity)
                o.stock_restored=True
            o.status=target; o.save(update_fields=['status','stock_restored'])
            if o.user_id: Notification.objects.create(user=o.user,order=o,kind='status_changed',status=target)
        return Response(OrderSerializer(o).data)
    @action(detail=True,methods=['post'],permission_classes=[AdminOnly])
    def payment(self,request,pk=None):
        o=self.get_object()
        if o.status!='delivered' or request.data.get('payment_status')!='paid': fail('payment_invalid')
        o.payment_status='paid'; o.save(update_fields=['payment_status'])
        return Response(OrderSerializer(o).data)

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model=Message
        fields=['id','body','seller','created','read']
        read_only_fields=['id','seller','created','read']
class ConversationSerializer(serializers.ModelSerializer):
    unread=serializers.SerializerMethodField()
    customer_name=serializers.CharField(source='customer.first_name',read_only=True)
    def get_unread(self,obj):
        return obj.messages.filter(read=False,seller=not self.context['request'].user.is_staff).count()
    class Meta:
        model=Conversation
        fields=['id','subject','product','order','customer_name','created','updated','unread']
    def validate(self,d):
        if d.get('order') and d['order'].user_id!=self.context['request'].user.pk and not self.context['request'].user.is_staff: raise PermissionDenied()
        if d.get('product') and not d['product'].active: fail('stock_unavailable')
        return d

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class=ConversationSerializer
    http_method_names=['get','post','head','options']
    def get_queryset(self):
        q=Conversation.objects.select_related('customer').prefetch_related('messages')
        return q if self.request.user.is_staff else q.filter(customer=self.request.user)
    def perform_create(self,s): s.save(customer=self.request.user)
    @action(detail=True,methods=['get','post'])
    def messages(self,request,pk=None):
        c=self.get_object()
        if request.method=='POST':
            s=MessageSerializer(data=request.data); s.is_valid(raise_exception=True)
            s.save(conversation=c,sender=request.user,seller=request.user.is_staff)
            c.save(update_fields=['updated'])
        c.messages.filter(seller=not request.user.is_staff,read=False).update(read=True)
        paginator=self.pagination_class()
        rows=paginator.paginate_queryset(c.messages.order_by('-created'),request)
        return paginator.get_paginated_response(MessageSerializer(rows,many=True).data)

class NotificationSerializer(serializers.ModelSerializer):
    amount=serializers.DecimalField(source='order.total',max_digits=14,decimal_places=2,read_only=True)
    currency=serializers.CharField(source='order.currency',read_only=True)
    customer=serializers.CharField(source='order.recipient',read_only=True)
    class Meta:
        model=Notification
        fields=['id','order','kind','status','read','created','amount','currency','customer']
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=NotificationSerializer
    def get_queryset(self): return Notification.objects.filter(user=self.request.user).select_related('order')
    @action(detail=True,methods=['post'])
    def mark_read(self,request,pk=None):
        obj=self.get_object(); obj.read=True; obj.save(update_fields=['read'])
        return Response({'ok':True})
    @action(detail=False,methods=['post'])
    def read_all(self,request):
        self.get_queryset().update(read=True)
        return Response({'ok':True})

@api_view(['GET'])
def dashboard(request):
    user=request.user; q=Order.objects.all() if user.is_staff else user.orders.all()
    data={'orders':q.count(),'active':q.exclude(status__in=['delivered','cancelled']).count(),'unread':user.notifications.filter(read=False).count(),'unread_messages':Message.objects.filter(conversation__in=Conversation.objects.all() if user.is_staff else user.conversations.all(),seller=not user.is_staff,read=False).count(),'recent':OrderSerializer(q.select_related('user').prefetch_related('items')[:5],many=True).data,'currency':settings.SHOP_CURRENCY}
    if user.is_staff:
        data.update(revenue=str(q.filter(status='delivered',payment_status='paid').aggregate(x=Sum('total'))['x'] or 0),low_stock=Variant.objects.filter(active=True,product__active=True,stock__lt=5).count(),customers=User.objects.filter(is_staff=False,is_active=True).count())
    return Response(data)

class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes=[AdminOnly]
    serializer_class=ProfileSerializer
    def get_queryset(self):
        q=User.objects.filter(is_staff=False,is_active=True).order_by('-date_joined')
        if self.request.query_params.get('search'):
            v=self.request.query_params['search']; q=q.filter(Q(first_name__icontains=v)|Q(email__icontains=v))
        return q

@api_view(['GET','PUT'])
@permission_classes([permissions.AllowAny])
def guide(request):
    config,_=GuideConfig.objects.get_or_create(pk=1,defaults={'data':{'steps':[],'faq':[]}})
    if request.method=='PUT':
        if not request.user.is_authenticated or not request.user.is_staff: raise PermissionDenied()
        data=request.data.get('data')
        if not isinstance(data,dict) or not isinstance(data.get('steps'),list) or not isinstance(data.get('faq'),list): fail('guide_invalid')
        allowed={'occasion','color','flower_type','max_price'}
        if len(data['steps'])>10 or len(data['faq'])>20: fail('guide_invalid')
        for step in data['steps']:
            if not isinstance(step,dict) or step.get('field') not in allowed or not isinstance(step.get('choices'),list) or not 1<=len(step['choices'])<=12: fail('guide_invalid')
            translations(step.get('question'))
            for choice in step['choices']:
                if not isinstance(choice,dict): fail('guide_invalid')
                translations(choice.get('label')); translations(choice.get('response'))
                if not isinstance(choice.get('value'),str) or len(choice['value'])>50: fail('guide_invalid')
                if step['field']=='max_price' and choice['value']:
                    try:
                        v=Decimal(choice['value'])
                        if not v.is_finite() or v<0: raise ValueError()
                    except Exception: fail('guide_invalid')
        for faq in data['faq']:
            if not isinstance(faq,dict): fail('guide_invalid')
            translations(faq.get('question')); translations(faq.get('answer'))
        config.data=data; config.save()
    return Response(config.data)

