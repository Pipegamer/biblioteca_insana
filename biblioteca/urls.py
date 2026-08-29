"""
=============================================================================
ENRUTAMIENTO PRINCIPAL DEL PROYECTO (biblioteca/urls.py)
=============================================================================
Conecta las vistas de autenticación, paneles de usuario (Lector y Administrador)
y los endpoints de la API RESTful.
=============================================================================
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from api import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # 1. PANTALLA PRINCIPAL DE ACCESO / LOGIN (Ruta Raíz)
    # -------------------------------------------------------------------------
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # -------------------------------------------------------------------------
    # 2. PANELES DE GESTIÓN SEGREGADOS POR ROLES (PROTEGIDOS CON LOGIN_REQUIRED)
    # -------------------------------------------------------------------------
    # Panel exclusivo para Administradores / Superusuarios
    path('dashboard-admin/', views.admin_dashboard_view, name='admin_dashboard'),

    # Portal exclusivo para Lectores (Usuarios normales)
    path('mi-biblioteca/', views.lector_dashboard_view, name='lector_dashboard'),

    # -------------------------------------------------------------------------
    # 3. PANEL DE ADMINISTRACIÓN NATIVO DE DJANGO
    # -------------------------------------------------------------------------
    path('admin/', admin.site.urls),

    # -------------------------------------------------------------------------
    # 4. ENDPOINTS RESTful DE LA APLICACIÓN 'api'
    # -------------------------------------------------------------------------
    path('api/', include('api.urls')),
]

# Servir archivos multimedia (portadas subidas desde el PC) en modo de desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
