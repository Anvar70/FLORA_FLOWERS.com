import json
from pathlib import Path
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from catalog.models import Category,Product,Variant
from core.models import GuideConfig
def T(en,uz,ru): return {'en':en,'uz':uz,'ru':ru}
class Command(BaseCommand):
    help='Idempotently create a translated sample catalog and deterministic guide. No accounts or fake orders.'
    @transaction.atomic
    def handle(self,*args,**opts):
        if Product.objects.exists():
            roses=Category.objects.filter(name__en='Signature bouquets').first()
            seasonal=Category.objects.filter(name__en='Seasonal stems').first()
            if roses and seasonal:
                self._add_products(roses, seasonal)
                self.stdout.write('Catalog already present; additional flowers checked.')
        else:
            roses=Category.objects.create(name=T('Signature bouquets','Maxsus guldastalar','Авторские букеты'),description=T('Thoughtful arrangements for meaningful moments.','Qadrli lahzalar uchun nafis guldastalar.','Букеты для важных мгновений.'))
            seasonal=Category.objects.create(name=T('Seasonal stems','Mavsumiy gullar','Сезонные цветы'),description=T('A little of the season, just for you.','Mavsum go‘zalligi siz uchun.','Красота сезона для вас.'))
            care=T('Trim stems at an angle. Refresh water daily. Keep cool and away from direct sunlight.','Poyani qiya kesing. Suvni har kuni almashtiring. Salqin, quyosh tushmaydigan joyda saqlang.','Подрежьте стебли под углом. Меняйте воду ежедневно. Держите в прохладе, вдали от солнца.')
            rows=[
                (T('Golden hour','Oltin lahza','Золотой час'),seasonal,'garden','yellow','thanks','seasonal_type',180000),
                (T('Wild poetry','Tabiat she’ri','Поэзия природы'),seasonal,'white','mixed','birthday','seasonal_type',290000),
                (T('Pink tulip','Pushti lola','Розовый тюльпан'),seasonal,'tulips','pink','everyday','tulips',95000),
                (T('Peach & promise','Mayin shaftoli','Персиковая нежность'),roses,'roses','pink','romance','roses',320000),
                (T('The Blush Edit','Nafis pushti','Нежный румянец'),roses,'hero','pink','birthday','roses',280000),
            ]
            for names,cat,asset,color,occasion,flower_type,price in rows:
                p=Product.objects.create(category=cat,name=names,description=T('A considered composition of seasonal flowers and natural greenery. Sample catalog arrangement; the seller confirms exact seasonal stems.','Mavsumiy gullar va tabiiy ko‘katlardan nafis kompozitsiya. Namunaviy katalog; aniq gullarni sotuvchi tasdiqlaydi.','Продуманная композиция сезонных цветов и зелени. Демонстрационный букет; точный состав подтверждает продавец.'),care=care,demo_asset='images/'+asset+'.jpg',color=color,occasion=occasion,flower_type=flower_type)
                for multiplier,names in [(1,T('Classic','Klassik','Классический')),(1.5,T('Abundant','Katta','Пышный'))]:
                    Variant.objects.create(product=p,name=names,price=Decimal(str(multiplier))*price,stock=20)
            self._add_products(roses, seasonal)
        if not GuideConfig.objects.filter(pk=1).exists():
            raw=json.loads((Path(__file__).resolve().parents[3]/'static'/'i18n.js').read_text(encoding='utf-8-sig').split('window.I18N=',1)[1].rstrip().rstrip(';'))
            def k(key): return dict(zip(['en','uz','ru'],raw[key]))
            def choices(keys): return [{'value':v,'label':k(label),'response':T('Lovely choice. Let’s narrow it down.','Ajoyib tanlov. Endi aniqlashtiramiz.','Прекрасный выбор. Уточним детали.')} for v,label in keys]
            GuideConfig.objects.create(pk=1,data={'steps':[
                {'field':'occasion','question':T('What is the occasion?','Qanday sabab uchun?','Какой повод?'),'choices':choices([(x,x) for x in ['birthday','romance','thanks','everyday']]+[('','all')])},
                {'field':'max_price','question':T('What budget feels right?','Qancha mablag‘ ajratmoqchisiz?','Какой бюджет вам подходит?'),'choices':[{'value':v,'label':T(l,l,l),'response':T('We will stay within your budget.','Belgilangan mablag‘ doirasida tanlaymiz.','Подберём в рамках бюджета.')} for v,l in [('200000','≤ 200 000 UZS'),('350000','≤ 350 000 UZS'),('','∞')]]},
                {'field':'color','question':T('Any favorite colors?','Qaysi ranglarni yoqtirasiz?','Какие цвета нравятся?'),'choices':choices([(x,x) for x in ['pink','white','yellow','mixed']]+[('','all')])},
                {'field':'flower_type','question':T('And your favorite flower?','Yoqtirgan gulingiz qaysi?','Любимые цветы?'),'choices':choices([(x,x) for x in ['roses','tulips','seasonal_type']]+[('','all')])}
            ],'faq':[{'question':k('faq_'+x),'answer':k('faq_'+x+'_a')} for x in ['delivery','payment','care']]})
        self.stdout.write(self.style.SUCCESS('Demo catalog and Flower Finder ready.'))

    def _add_products(self, roses, seasonal):
        care=T('Trim stems at an angle. Refresh water daily. Keep cool and away from direct sunlight.','Poyani qiya kesing. Suvni har kuni almashtiring. Salqin, quyosh tushmaydigan joyda saqlang.','Подрежьте стебли под углом. Меняйте воду ежедневно. Держите в прохладе, вдали от солнца.')
        rows=[
            (T('Red velvet','Qizil baxmal','Красный бархат'),roses,'red','red','romance','roses',260000),
            (T('Lavender cloud','Binafsha bulut','Лавандовое облако'),seasonal,'white','mixed','everyday','seasonal_type',210000),
            (T('Sunlit daisies','Quyoshli moychechak','Солнечные ромашки'),seasonal,'garden','yellow','thanks','seasonal_type',145000),
            (T('Cream romance','Kremli muhabbat','Кремовая любовь'),roses,'white','white','romance','roses',310000),
            (T('Spring tulips','Bahor lolalari','Весенние тюльпаны'),seasonal,'tulips','mixed','birthday','tulips',175000),
            (T('Garden gathering','Bog‘ ne’mati','Садовое настроение'),seasonal,'garden','mixed','birthday','seasonal_type',235000),
        ]
        for names,cat,asset,color,occasion,flower_type,price in rows:
            if Product.objects.filter(name__en=names['en']).exists(): continue
            p=Product.objects.create(category=cat,name=names,description=T('A considered composition of seasonal flowers and natural greenery. Sample catalog arrangement; the seller confirms exact seasonal stems.','Mavsumiy gullar va tabiiy ko‘katlardan nafis kompozitsiya. Namunaviy katalog; aniq gullarni sotuvchi tasdiqlaydi.','Продуманная композиция сезонных цветов и зелени. Демонстрационный букет; точный состав подтверждает продавец.'),care=care,demo_asset='images/'+asset+'.jpg',color=color,occasion=occasion,flower_type=flower_type)
            for multiplier,vnames in [(1,T('Classic','Klassik','Классический')),(1.5,T('Abundant','Katta','Пышный'))]:
                Variant.objects.create(product=p,name=vnames,price=Decimal(str(multiplier))*price,stock=20)

