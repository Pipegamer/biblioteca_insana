from datetime import date, timedelta
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Lector, Autor, Editorial, Libro, Prestamo

# =============================================================================
# PRUEBAS UNITARIAS Y DE INTEGRACIÓN (APITestCase)
# =============================================================================
# Valida autenticación por roles, vistas de dashboard, endpoints REST, 3NF
# y reglas de negocio (morosidad y borrado lógico).
# =============================================================================
class BibliotecaAPITests(APITestCase):

    def setUp(self):
        # 1. Crear Superusuario (Admin)
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            password='adminpassword123',
            email='admin@test.com'
        )

        # 2. Crear Usuario Normal (Lector)
        self.lector_user = User.objects.create_user(
            username='lector_test',
            password='lectorpassword123',
            first_name='Carlos',
            last_name='Mendoza Silva'
        )

        # 3. Crear Lector vinculado
        self.lector = Lector.objects.create(
            user=self.lector_user,
            rut='15.987.654-3',
            nombres="Carlos",
            apellido_p="Mendoza",
            apellido_m="Silva",
            is_active=True
        )

        # 4. Crear Autor, Editorial y Libro (3NF)
        self.autor = Autor.objects.create(nombre_autor="Gabriel García Márquez")
        self.editorial = Editorial.objects.create(nombre_editorial="Editorial Sudamericana")

        self.libro = Libro.objects.create(
            titulo="Cien Años de Soledad",
            descripcion="Obra cumbre del realismo mágico."
        )
        self.libro.autores.add(self.autor)
        self.libro.editoriales.add(self.editorial)

        self.url_lector_detail = reverse('lector-detail', kwargs={'pk': self.lector.pk})

    def test_login_view_renders(self):
        """
        Verifica que la pantalla de inicio de sesión ('/') cargue exitosamente.
        """
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Acceso al Sistema")
        self.assertContains(response, "Acceso Lector")
        self.assertContains(response, "Acceso Administrativo")

    def test_admin_dashboard_requires_login(self):
        """
        Verifica que el panel admin esté protegido y redirija al login si no está autenticado.
        """
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(response.url.startswith('/'))

    def test_admin_dashboard_accessible_by_superuser(self):
        """
        Verifica que un superusuario pueda acceder a /dashboard-admin/.
        """
        self.client.login(username='admin_test', password='adminpassword123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Panel de Control")

    def test_lector_dashboard_accessible_by_lector(self):
        """
        Verifica que un usuario lector pueda acceder a /mi-biblioteca/.
        """
        self.client.login(username='lector_test', password='lectorpassword123')
        response = self.client.get(reverse('lector_dashboard'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Mi Biblioteca")
        self.assertContains(response, "Catálogo de Libros Disponibles")

    def test_regla_morosidad_endpoint_mis_prestamos(self):
        """
        Verifica que si el lector tiene un préstamo con fecha_dev < hoy y devuelto=False,
        el endpoint mis-prestamos retorne tiene_morosidad=True.
        """
        # Crear préstamo vencido
        Prestamo.objects.create(
            fecha_dev=date.today() - timedelta(days=2),
            devuelto=False,
            libro=self.libro,
            lector=self.lector
        )

        self.client.login(username='lector_test', password='lectorpassword123')
        response = self.client.get(reverse('prestamo-mis-prestamos'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['tiene_morosidad'])

    def test_bloqueo_solicitud_con_morosidad(self):
        """
        Regla de negocio: Si el lector tiene un préstamo atrasado,
        el endpoint de solicitar préstamo rechaza la nueva reserva con HTTP 400.
        """
        Prestamo.objects.create(
            fecha_dev=date.today() - timedelta(days=2),
            devuelto=False,
            libro=self.libro,
            lector=self.lector
        )

        self.client.login(username='lector_test', password='lectorpassword123')
        response = self.client.post(
            reverse('prestamo-solicitar'),
            {'libro_id': self.libro.id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("atrasados", response.data['error'])

    def test_bloqueo_eliminacion_con_prestamo_activo(self):
        """
        Regla de negocio: Si el lector tiene un préstamo con devuelto=False,
        la petición DELETE debe retornar HTTP 400.
        """
        Prestamo.objects.create(
            fecha_dev=date.today() + timedelta(days=5),
            devuelto=False,
            libro=self.libro,
            lector=self.lector
        )

        response = self.client.delete(self.url_lector_detail)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No se puede eliminar el usuario", response.data["error"])

    def test_borrado_logico_sin_prestamos_activos(self):
        """
        Regla de negocio: Si el lector no tiene préstamos activos,
        la petición DELETE aplica is_active=False y retorna HTTP 204.
        """
        Prestamo.objects.create(
            fecha_dev=date.today() + timedelta(days=5),
            devuelto=True,
            libro=self.libro,
            lector=self.lector
        )

        response = self.client.delete(self.url_lector_detail)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.lector.refresh_from_db()
        self.assertFalse(self.lector.is_active)
        self.assertTrue(Lector.objects.filter(pk=self.lector.pk).exists())

    def test_devolver_prestamo_action(self):
        """
        Verifica que la acción /api/prestamos/{id}/devolver/ marque devuelto=True.
        """
        prestamo = Prestamo.objects.create(
            fecha_dev=date.today() + timedelta(days=5),
            devuelto=False,
            libro=self.libro,
            lector=self.lector
        )

        url_devolver = reverse('prestamo-devolver', kwargs={'pk': prestamo.pk})
        response = self.client.post(url_devolver)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        prestamo.refresh_from_db()
        self.assertTrue(prestamo.devuelto)

    def test_crear_libro_crud_con_precio_y_autores(self):
        """
        Verifica la creación de un nuevo libro en el catálogo con precio y relaciones.
        """
        url_libros = reverse('libro-list')
        data = {
            'titulo': 'Neuromante',
            'precio': 18990,
            'autor_nombre': 'William Gibson',
            'editorial_nombre': 'Minotauro',
            'descripcion': 'Clásico del cyberpunk.'
        }
        response = self.client.post(url_libros, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Libro.objects.filter(titulo='Neuromante').exists())
        nuevo_libro = Libro.objects.get(titulo='Neuromante')
        self.assertEqual(nuevo_libro.precio, 18990)
        self.assertTrue(nuevo_libro.autores.filter(nombre_autor='William Gibson').exists())

    def test_editar_libro_crud(self):
        """
        Verifica la edición/actualización de un libro existente en el catálogo.
        """
        url_libro_detail = reverse('libro-detail', kwargs={'pk': self.libro.pk})
        data = {
            'titulo': 'Cien Años de Soledad (Edición Conmemorativa)',
            'precio': 19990,
            'autor_nombre': 'Gabriel García Márquez',
            'editorial_nombre': 'Real Academia Española',
            'descripcion': 'Edición especial revisada por el autor.'
        }
        response = self.client.patch(url_libro_detail, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.libro.refresh_from_db()
        self.assertEqual(self.libro.titulo, 'Cien Años de Soledad (Edición Conmemorativa)')
        self.assertEqual(self.libro.precio, 19990)
        self.assertTrue(self.libro.editoriales.filter(nombre_editorial='Real Academia Española').exists())

    def test_reactivar_lector_desactivado(self):
        """
        Verifica que el endpoint /api/lectores/{id}/reactivar/ cambie is_active=True.
        """
        # Desactivar lector primero
        self.lector.is_active = False
        self.lector.save()

        url_reactivar = reverse('lector-reactivar', kwargs={'pk': self.lector.pk})
        response = self.client.post(url_reactivar)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.lector.refresh_from_db()
        self.assertTrue(self.lector.is_active)
