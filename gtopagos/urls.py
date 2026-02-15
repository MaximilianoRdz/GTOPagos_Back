"""
URL configuration for gtopagos project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from django.conf import settings
from django.views.generic import TemplateView
import sys
from django import get_version

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),
    path('api/', include('finance.urls')),
    path('api/', include('payments.urls')),
    path('api/', include('dashboard.urls')),
    # API Schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Solo ReDoc UI
    path('api/docs/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += [
        path("", TemplateView.as_view(
            template_name="index.html",
            extra_context={
                "django_version": get_version(),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
                "debug_mode": settings.DEBUG,
                "spectacular_settings": settings.SPECTACULAR_SETTINGS,
            }
        )),
    ]
