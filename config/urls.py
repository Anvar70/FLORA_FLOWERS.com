from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from rest_framework.routers import DefaultRouter
from core import api, views
router=DefaultRouter()
for name, view in [('products',api.ProductViewSet),('categories',api.CategoryViewSet),('variants',api.VariantViewSet),('addresses',api.AddressViewSet),('orders',api.OrderViewSet),('conversations',api.ConversationViewSet),('notifications',api.NotificationViewSet),('customers',api.CustomerViewSet)]:
    router.register(name,view,basename=name)
urlpatterns=[
    path('maintenance/',admin.site.urls),path('api/',include(router.urls)),
    path('api/profile/',api.profile),path('api/password/',api.password_change),path('api/email/',api.email_change),
    path('api/cart/',api.cart),path('api/checkout/',api.checkout),path('api/dashboard/',api.dashboard),path('api/guide/',api.guide),
    path('auth/<str:action>/',views.auth),path('reset/<uidb64>/<token>/',views.reset_confirm),
    path('email-confirm/<str:token>/',views.email_confirm),
    path('i18n/',include('django.conf.urls.i18n')),
]
if settings.DEBUG: urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
urlpatterns += [re_path(r'^(?P<path>(?:workspace|manage)(?:/.*)?|auth/|)$',views.page)]

