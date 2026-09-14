from pathlib import Path
p=Path('core/api.py');s=p.read_text(encoding='utf-8')
start=s.index("@api_view(['POST'])\ndef email_change")
end=s.index('\ndef cart_data',start)
s=s[:start]+"""@api_view(['POST'])
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
    send_mail(text,text+'\\n'+url,settings.DEFAULT_FROM_EMAIL,[email])
    return Response({'ok':True,'verification_required':True})
""" +s[end:]
p.write_text(s,encoding='utf-8')
p=Path('core/views.py');s=p.read_text(encoding='utf-8-sig')
s+="""
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
"""
p.write_text(s,encoding='utf-8')
p=Path('config/urls.py');s=p.read_text(encoding='utf-8-sig').replace("path('i18n/',","path('email-confirm/<str:token>/',views.email_confirm),\n    path('i18n/',");p.write_text(s,encoding='utf-8')
p=Path('config/settings.py');s=p.read_text(encoding='utf-8').replace("'django.template.context_processors.request',","'django.template.context_processors.request','django.template.context_processors.i18n',");p.write_text(s,encoding='utf-8')
p=Path('static/app.js');s=p.read_text(encoding='utf-8')
s=s.replace("await api('/api/email/','POST',d);toast(t('saved'));await profilePage();","await api('/api/email/','POST',d);toast(t('email_verification'));f.reset();")
s=s.replace("shell();\n try{","shell();syncDrawer();\n try{")
s=s.replace("FLORA / WELCOME</div>","FLORA / '+t('welcome')+'</div>")
s=s.replace("if(a==='menu'){const sidebar=$('#sidebar'),open=!sidebar.classList.contains('open');sidebar.classList.toggle('open',open);target.setAttribute('aria-expanded',String(open));if(open)$('a',sidebar).focus();}","if(a==='menu'){setDrawer(!$('#sidebar').classList.contains('open'));}")
s=s.replace("$('#sidebar')?.classList.remove('open');$('.mobile-menu')?.setAttribute('aria-expanded','false');","setDrawer(false);")
s=s.replace("const modal=$('.modal');\n if(modal&&e.key==='Tab')","const modal=$('.modal')||$('.sidebar.open');\n if(modal&&e.key==='Tab')")
s=s.replace("side.classList.remove('open');","setDrawer(false);")
s=s.replace("localStorage.setItem('flora-language',lang);render();","""function syncDrawer(){const side=$('#sidebar');if(side){side.inert=matchMedia('(max-width:900px)').matches&&!side.classList.contains('open');side.setAttribute('aria-hidden',String(side.inert));}}
function setDrawer(open){const side=$('#sidebar');if(!side)return;side.classList.toggle('open',open);syncDrawer();$('[data-action="menu"]')?.setAttribute('aria-expanded',String(open));if(open)$('a',side).focus();else $('[data-action="menu"]')?.focus();}
matchMedia('(max-width:900px)').addEventListener('change',syncDrawer);
localStorage.setItem('flora-language',lang);render();""")
p.write_text(s,encoding='utf-8')
p=Path('static/i18n.js');raw=p.read_text(encoding='utf-8-sig');import json
d=json.loads(raw.split('window.I18N=',1)[1].strip().rstrip(';'));d['email_verification']=['Check your new email for a confirmation link. Local demo: see the server email log.','Tasdiqlash havolasi uchun yangi pochtangizni tekshiring. Mahalliy demoda server pochta jurnaliga qarang.','Проверьте новую почту для подтверждения. В локальном демо смотрите журнал почты сервера.']
p.write_text('window.I18N='+json.dumps(d,ensure_ascii=False)+';\n',encoding='utf-8')

