from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LectorViewSet,
    AutorViewSet,
    EditorialViewSet,
    LibroViewSet,
    PrestamoViewSet,
)

# =============================================================================
# ENRUTADOR (DefaultRouter)
# =============================================================================
# El DefaultRouter genera automáticamente las rutas estándar RESTful para cada
# ViewSet registrado (list, create, retrieve, update, partial_update, destroy)
# y provee además una vista raíz navegable de la API (API Root).
# =============================================================================
router = DefaultRouter()

# Registro de endpoints
router.register(r'lectores', LectorViewSet, basename='lector')
router.register(r'autores', AutorViewSet, basename='autor')
router.register(r'editoriales', EditorialViewSet, basename='editorial')
router.register(r'libros', LibroViewSet, basename='libro')
router.register(r'prestamos', PrestamoViewSet, basename='prestamo')

# =============================================================================
# PATRONES DE URL DE LA APLICACIÓN 'api'
# =============================================================================
# Se incluyen todas las rutas generadas por el router para ser consumidas por
# el archivo de rutas principal del proyecto ('biblioteca/urls.py').
# =============================================================================
urlpatterns = [
    path('', include(router.urls)),
]
