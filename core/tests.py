import json, uuid
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone, translation
from django.conf import settings
from rest_framework.test import APIClient
from PIL import Image
from accounts.models import User,Address
from catalog.models import Category,Product,Variant
from orders.models import Order,OrderItem,Cart,CartItem
from messaging.models import Conversation,Message,Notification
from core.models import GuideConfig

@override_settings(CACHES={'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'}},PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ShopTests(TestCase):
    def setUp(self):
        self.customer=User.objects.create_user('a@example.test','a@example.test','Secure-pass-876!',first_name='Alice')
        self.other=User.objects.create_user('b@example.test','b@example.test','Secure-pass-876!',first_name='Bob')
        self.admin=User.objects.create_user('admin@example.test','admin@example.test','Secure-pass-876!',is_staff=True)
        names={'en':'Rose','uz':'Atirgul','ru':'Роза'}
        self.category=Category.objects.create(name=names,description=names)
        self.product=Product.objects.create(category=self.category,name=names,description=names,care=names,color='pink',occasion='birthday')
        self.variant=Variant.objects.create(product=self.product,name=names,price='100000.25',stock=5)
        self.client=APIClient();self.client.force_authenticate(self.customer)
    def add(self,quantity=2):
        return self.client.post('/api/cart/',{'variant':self.variant.pk,'quantity':quantity},format='json')
    def payload(self):
        return {'key':str(uuid.uuid4()),'recipient':'Alice','phone':'+998901234567','address':'Demo delivery address','delivery_date':str(timezone.localdate()+timedelta(days=1)),'slot':settings.DELIVERY_SLOTS[0],'gift_message':'<script>test</script>','total':'0.01'}
    def place(self):
        self.add();return self.client.post('/api/checkout/',self.payload(),format='json')
    def test_registration_never_elevates_role(self):
        c=Client()
        r=c.post('/auth/register/',json.dumps({'name':'New','email':'new@example.test','password':'Good-Password-726!','password_confirm':'Good-Password-726!','role':'admin','language':'en','is_staff':True}),content_type='application/json')
        self.assertEqual(r.status_code,403);self.assertFalse(User.objects.filter(email='new@example.test').exists())
        d={'name':'New','email':'new@example.test','password':'Good-Password-726!','password_confirm':'Good-Password-726!','role':'customer','language':'en','is_staff':True}
        r=c.post('/auth/register/',json.dumps(d),content_type='application/json')
        self.assertEqual(r.status_code,200);self.assertFalse(User.objects.get(email=d['email']).is_staff)
    def test_unauthorized_admin_endpoints(self):
        for url in ['/api/customers/','/api/variants/']:
            self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.post('/api/categories/',{},format='json').status_code,403)
        self.assertEqual(self.client.put('/api/guide/',{'data':{}},format='json').status_code,403)
        self.assertEqual(Client().get('/manage/overview/').status_code,302)
    def test_profile_fields_cannot_elevate_or_change_other_user(self):
        r=self.client.patch('/api/profile/',{'id':self.other.pk,'first_name':'Updated','is_staff':True,'email':'hacked@example.test'},format='json')
        self.assertEqual(r.status_code,200);self.customer.refresh_from_db();self.other.refresh_from_db()
        self.assertFalse(self.customer.is_staff);self.assertEqual(self.customer.email,'a@example.test');self.assertEqual(self.other.first_name,'Bob')
    def test_address_ownership_and_default(self):
        a=Address.objects.create(user=self.other,label='Home',recipient='Bob',phone='12345678',address='Elsewhere')
        self.assertEqual(self.client.patch(f'/api/addresses/{a.pk}/',{'label':'Hacked'},format='json').status_code,404)
        self.assertEqual(self.client.delete(f'/api/addresses/{a.pk}/').status_code,404)
        for n in range(2):
            self.assertEqual(self.client.post('/api/addresses/',{'label':str(n),'recipient':'Alice','phone':'12345678','address':'Demo address','is_default':True},format='json').status_code,201)
        self.assertEqual(Address.objects.filter(user=self.customer,is_default=True).count(),1)
    def test_conversation_isolation(self):
        c=Conversation.objects.create(customer=self.other,subject='Private')
        Message.objects.create(conversation=c,sender=self.other,body='Private message')
        self.assertEqual(self.client.get(f'/api/conversations/{c.pk}/messages/').status_code,404)
        self.assertEqual(self.client.post(f'/api/conversations/{c.pk}/messages/',{'body':'Hacked'},format='json').status_code,404)
    def test_messages_persist_and_unread(self):
        c=self.client.post('/api/conversations/',{'subject':'Flowers','product':self.product.pk},format='json').data
        url=f"/api/conversations/{c['id']}/messages/"
        self.assertEqual(self.client.post(url,{'body':'Hello seller'},format='json').status_code,200)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get('/api/dashboard/').data['unread_messages'],1)
        self.client.get(url)
        self.assertEqual(self.client.get('/api/dashboard/').data['unread_messages'],0)
        self.client.post(url,{'body':'Hello customer'},format='json')
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get('/api/dashboard/').data['unread_messages'],1)
        response=self.client.get(url)
        self.assertEqual(response.data['count'],2)
        self.assertEqual(self.client.post(url,{'body':'x'*2001},format='json').status_code,400)
    def test_cart_uses_decimal_server_price(self):
        self.assertEqual(self.add().status_code,200)
        c=self.client.get('/api/cart/').data
        self.assertEqual(Decimal(c['subtotal']),Decimal('200000.50'))
        self.assertEqual(Decimal(c['total']),Decimal('200000.50')+settings.SHOP_DELIVERY_FEE)
    def test_cart_invalid_quantity_and_ownership(self):
        for q in [0,-1,100,1.5]:
            self.assertEqual(self.add(q).status_code,400)
        self.add(1);self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/cart/').data['items'],[])
    def test_checkout_atomic_snapshots_and_notifications(self):
        r=self.place();self.assertEqual(r.status_code,201,r.data)
        o=Order.objects.get();self.variant.refresh_from_db()
        self.assertEqual(o.subtotal,Decimal('200000.50'));self.assertEqual(self.variant.stock,3)
        self.assertEqual(o.payment_method,'cod');self.assertEqual(o.payment_status,'unpaid')
        self.assertEqual(o.items.get().unit_price,Decimal('100000.25'))
        self.assertFalse(CartItem.objects.filter(cart__user=self.customer).exists())
        self.assertTrue(Notification.objects.filter(user=self.admin,order=o,kind='new_order').exists())
    def test_duplicate_submission_creates_one_order(self):
        self.add();d=self.payload()
        first=self.client.post('/api/checkout/',d,format='json')
        second=self.client.post('/api/checkout/',d,format='json')
        self.assertEqual(first.data['id'],second.data['id']);self.assertEqual(Order.objects.count(),1)
        self.variant.refresh_from_db();self.assertEqual(self.variant.stock,3)
    def test_stock_change_rolls_back_checkout_and_keeps_cart(self):
        self.add();self.variant.stock=1;self.variant.save()
        r=self.client.post('/api/checkout/',self.payload(),format='json')
        self.assertEqual(r.status_code,400);self.assertEqual(Order.objects.count(),0);self.assertEqual(CartItem.objects.count(),1)
        self.variant.refresh_from_db();self.assertEqual(self.variant.stock,1)
    def test_multiline_stock_failure_rolls_back_earlier_decrement(self):
        self.add()
        second=Variant.objects.create(product=self.product,name={'en':'Large'},price=200,stock=2)
        self.client.post('/api/cart/',{'variant':second.pk,'quantity':2},format='json')
        second.stock=0;second.save()
        self.assertEqual(self.client.post('/api/checkout/',self.payload(),format='json').status_code,400)
        self.variant.refresh_from_db();self.assertEqual(self.variant.stock,5);self.assertEqual(CartItem.objects.count(),2)
    def test_order_isolation(self):
        o=self.place().data
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/orders/{o['id']}/").status_code,404)
        self.assertEqual(self.client.get('/api/orders/').data['count'],0)
    def test_status_transitions_and_single_stock_restore(self):
        o=self.place().data;url=f"/api/orders/{o['id']}/transition/"
        self.assertEqual(self.client.post(url,{'status':'confirmed'},format='json').status_code,403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(url,{'status':'delivered'},format='json').status_code,400)
        self.assertEqual(self.client.post(url,{'status':'confirmed'},format='json').status_code,200)
        self.assertEqual(self.client.post(url,{'status':'cancelled'},format='json').status_code,200)
        self.assertEqual(self.client.post(url,{'status':'cancelled'},format='json').status_code,400)
        self.variant.refresh_from_db();self.assertEqual(self.variant.stock,5)
        self.assertEqual(Notification.objects.filter(user=self.customer,kind='status_changed').count(),2)
    def test_delivered_payment_and_revenue(self):
        o=self.place().data;self.client.force_authenticate(self.admin)
        url=f"/api/orders/{o['id']}/"
        self.assertEqual(self.client.post(url+'payment/',{'payment_status':'paid'},format='json').status_code,400)
        for s in ['confirmed','preparing','out_for_delivery','delivered']:
            self.assertEqual(self.client.post(url+'transition/',{'status':s},format='json').status_code,200)
        self.assertEqual(self.client.post(url+'payment/',{'payment_status':'paid'},format='json').status_code,200)
        self.assertEqual(Decimal(self.client.get('/api/dashboard/').data['revenue']),Decimal(o['total']))
    def test_archival_preserves_history(self):
        self.place();self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(f'/api/products/{self.product.pk}/').status_code,204)
        self.assertEqual(OrderItem.objects.count(),1)
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get(f'/api/products/{self.product.pk}/').status_code,404)
    def test_admin_can_see_products_without_variants(self):
        p=Product.objects.create(category=self.category,name={'en':'New'},description={'en':'New'},care={'en':'Care'},color='pink',occasion='birthday')
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(f'/api/products/{p.pk}/').status_code,200)
    def test_combined_filters_and_variant_budget(self):
        Variant.objects.create(product=self.product,name={'en':'Expensive'},price=300000,stock=1)
        r=self.client.get('/api/products/?color=pink&occasion=birthday&max_price=150000&available=true')
        self.assertEqual(r.data['count'],1);self.assertEqual(len(r.data['results'][0]['variants']),1)
        self.assertEqual(self.client.get('/api/products/?color=white&occasion=birthday').data['count'],0)
        self.assertEqual(self.client.get('/api/products/?max_price=NaN').status_code,400)
    def test_preferences_persist(self):
        self.client.patch('/api/profile/',{'language':'ru','theme':'dark'},format='json')
        d=self.client.get('/api/profile/').data
        self.assertEqual(d['language'],'ru');self.assertEqual(d['theme'],'dark')
    def test_account_deletion_anonymizes_orders(self):
        self.place()
        self.assertEqual(self.client.delete('/api/profile/',{'password':'wrong','confirm':True},format='json').status_code,400)
        self.assertEqual(self.client.delete('/api/profile/',{'password':'Secure-pass-876!','confirm':True},format='json').status_code,204)
        o=Order.objects.get();self.assertIsNone(o.user);self.assertEqual(o.phone,'');self.assertEqual(o.address,'');self.assertEqual(o.items.count(),1)
    def test_last_admin_cannot_delete_self(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete('/api/profile/',{'password':'Secure-pass-876!','confirm':True},format='json').status_code,400)
    def test_upload_validation(self):
        f=SimpleUploadedFile('bad.svg',b'<svg><script>alert(1)</script></svg>',content_type='image/svg+xml')
        self.assertEqual(self.client.patch('/api/profile/',{'avatar':f},format='multipart').status_code,400)
    def test_csrf_required_for_login_and_authenticated_mutation(self):
        c=Client(enforce_csrf_checks=True)
        self.assertEqual(c.post('/auth/login/',json.dumps({'email':'a@example.test','password':'Secure-pass-876!'}),content_type='application/json').status_code,403)
        c.force_login(self.customer)
        self.assertEqual(c.post('/api/cart/',json.dumps({'variant':self.variant.pk,'quantity':1}),content_type='application/json').status_code,403)
    def test_guide_validation_and_permissions(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.put('/api/guide/',{'data':{'steps':[{'field':'arbitrary','choices':[]}],'faq':[]}},format='json').status_code,400)
    def test_notification_isolation(self):
        self.place();n=Notification.objects.get(user=self.admin)
        self.assertEqual(self.client.post(f'/api/notifications/{n.pk}/mark_read/',{},format='json').status_code,404)
    def test_translation_dictionary_complete(self):
        raw=(settings.BASE_DIR/'static/i18n.js').read_text(encoding='utf-8-sig')
        d=json.loads(raw.split('window.I18N=',1)[1].strip().rstrip(';'))
        for key,values in d.items():
            self.assertEqual(len(values),3,key);self.assertTrue(all(isinstance(v,str) and v for v in values),key)


    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_email_change_requires_new_email_confirmation(self):
        from django.core import mail
        from urllib.parse import urlparse
        r=self.client.post('/api/email/',{'email':'new@example.test','password':'Secure-pass-876!'},format='json')
        self.assertEqual(r.status_code,200)
        self.customer.refresh_from_db();self.assertEqual(self.customer.email,'a@example.test')
        url=mail.outbox[0].body.splitlines()[-1]
        path=urlparse(url).path
        c=Client();self.assertEqual(c.get(path).status_code,200)
        self.customer.refresh_from_db();self.assertEqual(self.customer.email,'a@example.test')
        self.assertEqual(c.post(path).status_code,200)
        self.customer.refresh_from_db();self.assertEqual(self.customer.email,'new@example.test')
        self.assertEqual(self.customer.username,'new@example.test')
    def test_password_change_checks_current_password(self):
        self.assertEqual(self.client.post('/api/password/',{'current_password':'wrong','password':'Updated-pass-876!'},format='json').status_code,400)
        self.assertEqual(self.client.post('/api/password/',{'current_password':'Secure-pass-876!','password':'Updated-pass-876!'},format='json').status_code,200)
        self.customer.refresh_from_db();self.assertTrue(self.customer.check_password('Updated-pass-876!'))
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_token_journey(self):
        from django.core import mail
        from urllib.parse import urlparse
        c=Client()
        r=c.post('/auth/reset/',json.dumps({'email':self.customer.email,'language':'en'}),content_type='application/json')
        self.assertEqual(r.status_code,200);self.assertEqual(len(mail.outbox),1)
        url=next(line for line in mail.outbox[0].body.splitlines() if line.startswith('http'))
        reset_path=urlparse(url).path
        self.assertEqual(c.post(reset_path,{'new_password1':'New-Password-936!','new_password2':'New-Password-936!'}).status_code,200)
        self.customer.refresh_from_db();self.assertTrue(self.customer.check_password('New-Password-936!'))
    def test_avatar_upload_removal(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder,override_settings(MEDIA_ROOT=folder):
            image=BytesIO();Image.new('RGB',(20,20),'red').save(image,format='PNG')
            f=SimpleUploadedFile('avatar.png',image.getvalue(),content_type='image/png')
            r=self.client.patch('/api/profile/',{'avatar':f},format='multipart')
            self.assertEqual(r.status_code,200)
            self.customer.refresh_from_db();name=self.customer.avatar.name;storage=self.customer.avatar.storage
            self.assertTrue(storage.exists(name))
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.client.patch('/api/profile/',{'avatar':None},format='json').status_code,200)
            self.assertFalse(storage.exists(name))
    def test_admin_product_and_category_crud(self):
        self.client.force_authenticate(self.admin)
        names={'en':'New','uz':'Yangi','ru':'Новый'}
        r=self.client.post('/api/categories/',{'name':json.dumps(names),'description':json.dumps(names),'active':'true'},format='multipart')
        self.assertEqual(r.status_code,201,r.data)
        category=r.data['id']
        product=self.client.post('/api/products/',{'category':category,'name':json.dumps(names),'description':json.dumps(names),'care':json.dumps(names),'color':'pink','occasion':'birthday','flower_type':'roses','active':'true'},format='multipart')
        self.assertEqual(product.status_code,201,product.data)
        pid=product.data['id']
        v=self.client.post('/api/variants/',{'product':pid,'name':names,'price':'12345.67','stock':10},format='json')
        self.assertEqual(v.status_code,201,v.data)
        self.assertEqual(self.client.patch(f"/api/variants/{v.data['id']}/",{'stock':3},format='json').status_code,200)
        self.assertEqual(self.client.delete(f'/api/categories/{category}/').status_code,204)
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get(f'/api/products/{pid}/').status_code,404)
    def test_django_translation_catalog(self):
        from django.utils.translation import gettext
        with translation.override('uz'): self.assertEqual(gettext('Reset your password'),'Parolingizni tiklang')
        with translation.override('ru'): self.assertEqual(gettext('Email updated successfully.'),'Электронная почта обновлена.')
    def test_order_dates_and_archived_stock_rejected(self):
        self.add();data=self.payload();data['delivery_date']=str(timezone.localdate())
        self.assertEqual(self.client.post('/api/checkout/',data,format='json').status_code,400)
        self.category.active=False;self.category.save()
        self.assertEqual(self.client.post('/api/checkout/',self.payload(),format='json').status_code,400)
        self.variant.refresh_from_db();self.assertEqual(self.variant.stock,5)
    def test_guide_malformed_choices_rejected(self):
        self.client.force_authenticate(self.admin)
        bad={'steps':[{'field':'color','question':{'en':'Color'},'choices':[None]}],'faq':[]}
        self.assertEqual(self.client.put('/api/guide/',{'data':bad},format='json').status_code,400)

