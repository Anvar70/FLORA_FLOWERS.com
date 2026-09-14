import json, hashlib
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.core.validators import validate_email
from django.db import IntegrityError
from django.conf import settings
from django.utils import translation
from django.utils.http import urlsafe_base64_decode
from accounts.models import User

@ensure_csrf_cookie
def page(request, path=''):
    if path.startswith('workspace') and not request.user.is_authenticated: return redirect('/auth/')
    if path.startswith('manage') and not (request.user.is_authenticated and request.user.is_staff): return redirect('/auth/?role=admin')
    if path.startswith('workspace') and request.user.is_staff: return redirect('/manage/overview/')
    return render(request,'app.html',{'boot':{'user':{'id':request.user.pk,'name':request.user.first_name,'is_staff':request.user.is_staff,'language':request.user.language,'theme':request.user.theme} if request.user.is_authenticated else None,'currency':settings.SHOP_CURRENCY,'delivery_fee':str(settings.SHOP_DELIVERY_FEE),'contact':settings.SHOP_CONTACT,'slots':settings.DELIVERY_SLOTS,'demo':True}})

def err(code,status=400): return JsonResponse({'error':{'code':code}},status=status)
@require_POST
@csrf_protect
def auth(request, action):
    try: d=json.loads(request.body)
    except (ValueError,UnicodeDecodeError): return err('invalid_form')
    if not isinstance(d,dict): return err('invalid_form')
    language=d.get('language','uz')
    if language not in ['uz','en','ru']: return err('invalid_form')
    translation.activate(language)
    if action=='logout':
        logout(request); return JsonResponse({'ok':True})
    if action not in ['login','register','reset']: return err('invalid_form')
    email=str(d.get('email','')).strip().lower()
    ipkey='auth-ip-'+hashlib.sha256(request.META.get('REMOTE_ADDR','').encode()).hexdigest()
    accountkey='auth-account-'+hashlib.sha256(email.encode()).hexdigest()
    for key in [ipkey,accountkey]:
        cache.add(key,0,900)
        if cache.incr(key)>20: return err('try_later',429)
    try: validate_email(email)
    except ValidationError: return err('email_invalid')
    if action=='reset':
        form=PasswordResetForm({'email':email})
        if form.is_valid(): form.save(request=request,use_https=request.is_secure(),email_template_name='registration/password_reset_email.html',subject_template_name='registration/password_reset_subject.txt')
        return JsonResponse({'ok':True})
    password=d.get('password','')
    if not isinstance(password,str): return err('invalid_form')
    if action=='register':
        if d.get('role')=='admin': return err('admin_registration_forbidden',403)
        if password!=d.get('password_confirm'): return err('password_mismatch')
        name=str(d.get('name','')).strip()
        if not name or len(name)>150: return err('name_required')
        user=User(username=email,email=email,first_name=name,language=language)
        try: validate_password(password,user)
        except ValidationError: return err('password_weak')
        try:
            user.set_password(password); user.save()
        except IntegrityError: return err('email_taken')
    else:
        user=authenticate(request,username=email,password=password)
        if user is None: return err('login_invalid',400)
        if d.get('role')=='admin' and not user.is_staff: return err('admin_forbidden',403)
    login(request,user)
    # Existing profiles take precedence; registration saves the selected language.
    response=JsonResponse({'redirect':'/manage/overview/' if user.is_staff else '/workspace/dashboard/'})
    response.set_cookie('django_language',user.language,samesite='Lax',secure=not settings.DEBUG)
    return response

@csrf_protect
def reset_confirm(request,uidb64,token):
    try: user=User.objects.get(pk=urlsafe_base64_decode(uidb64).decode())
    except (ValueError,User.DoesNotExist,UnicodeDecodeError): user=None
    if not user or not default_token_generator.check_token(user,token): return render(request,'registration/reset.html',{'invalid':True})
    form=SetPasswordForm(user,request.POST or None)
    if request.method=='POST' and form.is_valid():
        form.save(); return render(request,'registration/reset.html',{'done':True})
    return render(request,'registration/reset.html',{'form':form})


@csrf_protect
def email_confirm(request,token):
    from django.core import signing
    from hashlib import sha256
    from django.db import transaction
    invalid=False; done=False
    try:
        data=signing.loads(token,salt='email-change',max_age=3600)
        user=User.objects.get(pk=data['uid'],is_active=True,email=data['old_email'])
        if sha256(user.password.encode()).hexdigest()!=data['password_digest']: raise ValueError()
        if request.method=='POST':
            with transaction.atomic():
                user.email=data['email'];user.username=data['email'];user.save(update_fields=['email','username'])
            done=True
    except (signing.BadSignature,User.DoesNotExist,ValueError,KeyError,IntegrityError):
        invalid=True
    return render(request,'registration/email_confirm.html',{'invalid':invalid,'done':done})
