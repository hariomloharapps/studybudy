
# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('app-info/', views.app_info, name='app_info'),
]