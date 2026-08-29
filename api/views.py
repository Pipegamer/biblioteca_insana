from datetime import date, timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Lector, Autor, Editorial, Libro, Prestamo
from .serializers import (
    LectorSerializer,
    AutorSerializer,
    EditorialSerializer,
    LibroSerializer,
    PrestamoSerializer,
)


# =============================================================================
# VISTAS DE AUTENTICACIÓN Y ROLES (DJANGO AUTH)
# =============================================================================

@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    Vista principal de inicio de sesión:
    - GET: Renderiza 'login.html' con los paneles separados para Lector y Administrador.
    - POST: Valida credenciales según el tipo de formulario enviado:
        * Login Administrador: Valida superusuario/staff y redirige a /dashboard-admin/
        * Login Lector: Valida RUT o Usuario del lector y redirige a /mi-biblioteca/
    """
    # Si el usuario ya está autenticado, redirigir según su rol
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('lector_dashboard')

    if request.method == 'POST':
        tipo_login = request.POST.get('tipo_login', 'lector')

        # ---------------------------------------------------------------------
        # 1. LOGIN DE ADMINISTRADOR
        # ---------------------------------------------------------------------
        if tipo_login == 'admin':
            usuario = request.POST.get('admin_username', '').strip()
            clave = request.POST.get('admin_password', '')

            user = authenticate(request, username=usuario, password=clave)

            if user is not None:
                if user.is_superuser or user.is_staff:
                    auth_login(request, user)
                    return redirect('admin_dashboard')
                else:
                    messages.error(
                        request,
                        "Acceso Denegado: La cuenta no cuenta con permisos de Administrador.",
                        extra_tags="admin"
                    )
            else:
                messages.error(
                    request,
                    "Credenciales de administrador inválidas.",
                    extra_tags="admin"
                )

        # ---------------------------------------------------------------------
        # 2. LOGIN DE LECTOR (USUARIO NORMAL)
        # ---------------------------------------------------------------------
        else:
            identificador = request.POST.get('lector_identificador', '').strip()
            clave = request.POST.get('lector_password', '')

            # Intentar autenticación directa por username
            user = authenticate(request, username=identificador, password=clave)

            # Si no funciona por username, buscar si coincide con el RUT de un lector
            if user is None:
                lector_match = Lector.objects.filter(rut=identificador, is_active=True).first()
                if lector_match and lector_match.user:
                    user = authenticate(request, username=lector_match.user.username, password=clave)

            if user is not None:
                # Validar estado activo si tiene perfil de lector
                lector_perfil = getattr(user, 'lector_profile', None)
                if lector_perfil and not lector_perfil.is_active:
                    messages.error(
                        request,
                        "Tu cuenta de lector ha sido desactivada. Consulta en biblioteca.",
                        extra_tags="lector"
                    )
                else:
                    auth_login(request, user)
                    return redirect('lector_dashboard')
            else:
                messages.error(
                    request,
                    "RUT/ID o contraseña de lector incorrectos.",
                    extra_tags="lector"
                )

    return render(request, 'login.html')


def logout_view(request):
    """
    Cierra la sesión del usuario actual y redirige a la pantalla de inicio de sesión.
    """
    auth_logout(request)
    return redirect('login')


# =============================================================================
# VISTAS DE PANELES (DASHBOARDS PROTEGIDOS POR LOGIN_REQUIRED)
# =============================================================================

@login_required(login_url='/')
def admin_dashboard_view(request):
    """
    Panel exclusivo para Administradores:
    - Gestiona el CRUD de lectores (formulario de registro y listado de eliminación).
    - Gestiona el CRUD completo del Catálogo de Libros (con precios y carga de fotos desde PC).
    - Aplica la regla de borrado lógico y bloqueo de préstamos activos.
    """
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('lector_dashboard')

    autores = Autor.objects.all()
    editoriales = Editorial.objects.all()

    return render(request, 'admin_dashboard.html', {
        'autores': autores,
        'editoriales': editoriales
    })


@login_required(login_url='/')
def lector_dashboard_view(request):
    """
    Panel exclusivo para el Lector (Usuario Normal):
    - Despliega mensaje de bienvenida personalizado.
    - Muestra el catálogo de libros disponibles para reservar con precios y portadas.
    - Muestra los préstamos del usuario con opción de devolución inmediata.
    """
    lector_perfil = getattr(request.user, 'lector_profile', None)
    if lector_perfil is None:
        lector_perfil = Lector.objects.filter(is_active=True).first()

    contexto = {
        'lector': lector_perfil,
        'nombre_mostrado': request.user.get_full_name() or (str(lector_perfil) if lector_perfil else request.user.username)
    }
    return render(request, 'lector_dashboard.html', contexto)


# =============================================================================
# API REST (ModelViewSet) Y REGLAS DE NEGOCIO
# =============================================================================

class LectorViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la gestión de Lectores con borrado lógico y regla de integridad.
    """
    queryset = Lector.objects.all()
    serializer_class = LectorSerializer

    def destroy(self, request, *args, **kwargs):
        lector = self.get_object()

        tiene_prestamos_activos = lector.prestamos.filter(devuelto=False).exists()

        if tiene_prestamos_activos:
            return Response(
                {"error": "No se puede eliminar el usuario porque tiene libros sin devolver"},
                status=status.HTTP_400_BAD_REQUEST
            )

        lector.is_active = False
        lector.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'patch'], url_path='reactivar')
    def reactivar(self, request, pk=None):
        """
        Reactiva un lector previamente desactivado (is_active = True).
        Permite restaurar su acceso al sistema y habilitar nuevas operaciones.
        """
        lector = self.get_object()
        lector.is_active = True
        lector.save()
        serializer = self.get_serializer(lector)
        return Response({
            'mensaje': f'El lector "{lector}" ha sido reactivado exitosamente.',
            'lector': serializer.data
        }, status=status.HTTP_200_OK)


class AutorViewSet(viewsets.ModelViewSet):
    queryset = Autor.objects.all()
    serializer_class = AutorSerializer


class EditorialViewSet(viewsets.ModelViewSet):
    queryset = Editorial.objects.all()
    serializer_class = EditorialSerializer


class LibroViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la administración completa del Catálogo de Libros:
    - Admite subida de archivos multipart (imágenes desde PC)
    - Admite gestión de precios y relaciones N:M 3NF con Autores y Editoriales
    """
    queryset = Libro.objects.all().order_by('-id')
    serializer_class = LibroSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _procesar_relaciones(self, libro, data):
        """
        Helper para sincronizar autores y editoriales (3NF N:M) al crear o editar.
        """
        autores_input = data.get('autor_nombre') or data.getlist('autores') if hasattr(data, 'getlist') else data.get('autores')
        editoriales_input = data.get('editorial_nombre') or data.getlist('editoriales') if hasattr(data, 'getlist') else data.get('editoriales')

        if autores_input:
            libro.autores.clear()
            if isinstance(autores_input, list):
                for a_item in autores_input:
                    if str(a_item).isdigit():
                        libro.autores.add(int(a_item))
                    elif a_item:
                        a_obj, _ = Autor.objects.get_or_create(nombre_autor=str(a_item).strip())
                        libro.autores.add(a_obj)
            elif isinstance(autores_input, str):
                for a_nombre in autores_input.split(','):
                    if a_nombre.strip().isdigit():
                        libro.autores.add(int(a_nombre.strip()))
                    elif a_nombre.strip():
                        a_obj, _ = Autor.objects.get_or_create(nombre_autor=a_nombre.strip())
                        libro.autores.add(a_obj)

        if editoriales_input:
            libro.editoriales.clear()
            if isinstance(editoriales_input, list):
                for e_item in editoriales_input:
                    if str(e_item).isdigit():
                        libro.editoriales.add(int(e_item))
                    elif e_item:
                        e_obj, _ = Editorial.objects.get_or_create(nombre_editorial=str(e_item).strip())
                        libro.editoriales.add(e_obj)
            elif isinstance(editoriales_input, str):
                for e_nombre in editoriales_input.split(','):
                    if e_nombre.strip().isdigit():
                        libro.editoriales.add(int(e_nombre.strip()))
                    elif e_nombre.strip():
                        e_obj, _ = Editorial.objects.get_or_create(nombre_editorial=e_nombre.strip())
                        libro.editoriales.add(e_obj)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        libro = serializer.save()

        self._procesar_relaciones(libro, data)

        headers = self.get_success_headers(serializer.data)
        out_serializer = self.get_serializer(libro, context={'request': request})
        return Response(out_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.copy()

        # Si no se envía imagen nueva en la edición, no sobrescribir la existente
        if 'imagen' in data and not data['imagen']:
            data.pop('imagen')

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        libro = serializer.save()

        self._procesar_relaciones(libro, data)

        out_serializer = self.get_serializer(libro, context={'request': request})
        return Response(out_serializer.data, status=status.HTTP_200_OK)


class PrestamoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para préstamos con endpoints personalizados para morosidad, reservas y devolución.
    """
    queryset = Prestamo.objects.all()
    serializer_class = PrestamoSerializer

    @action(detail=False, methods=['get'], url_path='mis-prestamos')
    def mis_prestamos(self, request):
        """
        Devuelve los préstamos del usuario actualmente autenticado y evalúa morosidad.
        """
        lector = None
        if request.user.is_authenticated:
            lector = getattr(request.user, 'lector_profile', None)

        if not lector:
            lector_id = request.query_params.get('lector_id')
            if lector_id:
                lector = Lector.objects.filter(id=lector_id).first()

        if not lector:
            lector = Lector.objects.filter(is_active=True).first()

        if not lector:
            return Response({'prestamos': [], 'tiene_morosidad': False})

        prestamos_qs = Prestamo.objects.filter(lector=lector).order_by('-id')
        serializer = PrestamoSerializer(prestamos_qs, many=True, context={'request': request})

        # Evaluación de regla de morosidad
        tiene_morosidad = any(item.get('atrasado', False) for item in serializer.data)

        return Response({
            'lector_id': lector.id,
            'lector_nombre': str(lector),
            'tiene_morosidad': tiene_morosidad,
            'prestamos': serializer.data
        })

    @action(detail=False, methods=['post'], url_path='solicitar')
    def solicitar(self, request):
        """
        Permite a un lector solicitar un préstamo verificando antes que no tenga morosidad.
        """
        libro_id = request.data.get('libro_id')
        if not libro_id:
            return Response(
                {'error': 'Debe especificar el libro a reservar.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        libro = Libro.objects.filter(id=libro_id).first()
        if not libro:
            return Response(
                {'error': 'El libro solicitado no existe.'},
                status=status.HTTP_404_NOT_FOUND
            )

        lector = getattr(request.user, 'lector_profile', None)
        if not lector:
            lector_id = request.data.get('lector_id')
            if lector_id:
                lector = Lector.objects.filter(id=lector_id, is_active=True).first()

        if not lector:
            lector = Lector.objects.filter(is_active=True).first()

        if not lector or not lector.is_active:
            return Response(
                {'error': 'No se encontró un perfil de lector activo para realizar la reserva.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Regla de negocio: Verificar morosidad antes de prestar
        hoy = date.today()
        prestamo_moroso = Prestamo.objects.filter(
            lector=lector,
            devuelto=False,
            fecha_dev__lt=hoy
        ).exists()

        if prestamo_moroso:
            return Response(
                {'error': 'Advertencia: Tienes préstamos atrasados. Por favor devuelve los libros pendientes para realizar nuevas reservas.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        nuevo_prestamo = Prestamo.objects.create(
            libro=libro,
            lector=lector,
            fecha_dev=hoy + timedelta(days=7),
            devuelto=False
        )

        serializer = PrestamoSerializer(nuevo_prestamo, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post', 'patch'], url_path='devolver')
    def devolver(self, request, pk=None):
        """
        Marca un préstamo como devuelto (devuelto=True).
        Libera al lector de cualquier bloqueo de morosidad asociado al libro.
        """
        prestamo = self.get_object()
        prestamo.devuelto = True
        prestamo.save()

        serializer = PrestamoSerializer(prestamo, context={'request': request})
        return Response({
            'mensaje': f'El libro "{prestamo.libro.titulo}" ha sido devuelto exitosamente a la biblioteca.',
            'prestamo': serializer.data
        }, status=status.HTTP_200_OK)
