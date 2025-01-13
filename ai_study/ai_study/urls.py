
# ai_study/urls.py (project level)
from django.contrib import admin
from django.urls import path, include
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('app.urls')),
    path('api/', include('q_and_a.urls')),
    path('api/accounts/', include('accounts.urls')),
    path('api/utils/', include('utils.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
