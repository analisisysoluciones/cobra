"""
URL configuration for cobra project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
#from adm.api import api_equipos_activos
#from adm.views_flotilla import flotilla_captura





urlpatterns = [
    path('',include(('bases.urls','bases'), namespace='bases')),
    path('inv/',include(('inv.urls','inv'), namespace='inv')),
    path('adm/',include(('adm.urls','adm'), namespace='adm')),
    path('nom/', include(('nomina.urls','nom'),namespace='nom')),
    path('ven/',include(('ventas.urls','ventas'), namespace='ven')),
    path('cxp/',include(('cxp.urls','cxp'), namespace='cxp')),
    path('finanzas/',include(('finanzas.urls','cxp'), namespace='finanzas')),
    path('renta/',include(('renta.urls','renta'), namespace='renta')),
    path('admin/', admin.site.urls),
    #path('api/equipos-activos/', api_equipos_activos, name='api_equipos_activos'),
    #path('flotilla/captura/', flotilla_captura, name='flotilla_captura'),
    
    
    
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    

    



