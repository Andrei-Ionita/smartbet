from django.urls import path, include
from django.contrib import admin

# Minimal URLs - using Next.js frontend with SportMonks API
# Keeping this file for Django admin compatibility

urlpatterns = [
    path('admin/', admin.site.urls), # Django admin
    path('api/', include('core.api.urls')), # Sentiment analysis API
]
