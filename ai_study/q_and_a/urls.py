# tests/urls.py
from django.urls import path
from .views import generate_test

urlpatterns = [
    # path('tests/create/', CreateTestView.as_view(), name='create-test'),
    path('generate_test/', generate_test, name='test-list'),
]