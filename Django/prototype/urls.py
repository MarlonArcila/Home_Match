from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from v1_app.views import register, login
from django.conf import settings
from rest_framework.authtoken.views import obtain_auth_token 

router = DefaultRouter()

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/', include(router.urls)), 
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('register/', register, name='register'),
    path('login/', login, name='login'),
]

