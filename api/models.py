from django.db import models
from django.contrib.auth.models import User

# =============================================================================
# MODELO: Lector
# =============================================================================
# Representa a los usuarios/lectores de la biblioteca.
# Aplicación de 3NF (Tercera Forma Normal):
# - Atomicidad de atributos: En lugar de un campo "nombre_completo", se separa en
#   'nombres', 'apellido_p' (paterno) y 'apellido_m' (materno).
# - Identificador: 'rut' almacena el identificador único o RUT del lector.
# - Integración con Auth: 'user' vincula al lector con la cuenta de usuario de Django.
# - Borrado Lógico: 'is_active' permite deshabilitar al lector sin eliminar físicamente
#   sus registros ni perder la integridad referencial de su historial de préstamos.
# =============================================================================
class Lector(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="lector_profile",
        verbose_name="Usuario del Sistema",
        help_text="Cuenta de usuario de Django asociada para inicio de sesión"
    )
    rut = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="RUT / Identificador",
        help_text="RUT o identificador de credencial del lector"
    )
    nombres = models.CharField(
        max_length=100,
        verbose_name="Nombres",
        help_text="Nombres de pila del lector (campo atómico)"
    )
    apellido_p = models.CharField(
        max_length=100,
        verbose_name="Apellido Paterno",
        help_text="Primer apellido del lector (campo atómico)"
    )
    apellido_m = models.CharField(
        max_length=100,
        verbose_name="Apellido Materno",
        help_text="Segundo apellido del lector (campo atómico)"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Bandera para borrado lógico. True = Activo, False = Inactivo"
    )

    class Meta:
        verbose_name = "Lector"
        verbose_name_plural = "Lectores"

    def __str__(self):
        return f"{self.nombres} {self.apellido_p} {self.apellido_m}"


# =============================================================================
# MODELO: Autor
# =============================================================================
# Representa a los autores de los libros.
# Aplicación de 3NF:
# - Se aísla el autor en su propia entidad para evitar redundancia y anomalías de
#   actualización en los libros.
# =============================================================================
class Autor(models.Model):
    nombre_autor = models.CharField(
        max_length=150,
        verbose_name="Nombre del Autor",
        help_text="Nombre completo o identificador del autor"
    )

    class Meta:
        verbose_name = "Autor"
        verbose_name_plural = "Autores"

    def __str__(self):
        return self.nombre_autor


# =============================================================================
# MODELO: Editorial
# =============================================================================
# Representa a las editoriales o casas publicadoras.
# Aplicación de 3NF:
# - Se desacopla la editorial del libro para normalizar los datos y evitar duplicidad.
# =============================================================================
class Editorial(models.Model):
    nombre_editorial = models.CharField(
        max_length=150,
        verbose_name="Nombre de la Editorial",
        help_text="Nombre de la casa editorial"
    )

    class Meta:
        verbose_name = "Editorial"
        verbose_name_plural = "Editoriales"

    def __str__(self):
        return self.nombre_editorial


# =============================================================================
# MODELO: Libro
# =============================================================================
# Representa los títulos disponibles en la biblioteca.
# Aplicación de 3NF y Relaciones Muchos a Muchos (N:M):
# - Un libro puede tener múltiples autores y un autor múltiples libros (N:M).
# - Un libro puede ser coeditado por múltiples editoriales o una editorial tener
#   múltiples libros (N:M).
# - Django resuelve automáticamente las tablas intermedias/puente ('api_libro_autores'
#   y 'api_libro_editoriales') manteniendo la 3NF sin necesidad de crearlas manualmente.
# =============================================================================
class Libro(models.Model):
    titulo = models.CharField(
        max_length=200,
        verbose_name="Título del Libro",
        help_text="Título de la obra literaria"
    )
    descripcion = models.TextField(
        blank=True,
        default="",
        verbose_name="Sinopsis / Descripción",
        help_text="Breve resumen del libro"
    )
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=9990,
        verbose_name="Precio ($ CLP)",
        help_text="Precio de venta o valor de arriendo del libro"
    )
    imagen = models.ImageField(
        upload_to="portadas/",
        null=True,
        blank=True,
        verbose_name="Imagen de Portada",
        help_text="Imagen referencial del libro subida desde el ordenador"
    )
    autores = models.ManyToManyField(
        Autor,
        related_name="libros",
        verbose_name="Autores",
        help_text="Autores asociados al libro (relación N:M)"
    )
    editoriales = models.ManyToManyField(
        Editorial,
        related_name="libros",
        verbose_name="Editoriales",
        help_text="Editoriales asociadas al libro (relación N:M)"
    )

    class Meta:
        verbose_name = "Libro"
        verbose_name_plural = "Libros"

    def __str__(self):
        return self.titulo


# =============================================================================
# MODELO: Prestamo
# =============================================================================
# Representa una transacción de préstamo de un libro a un lector.
# Conexión relacional (1:N):
# - Clave foránea (FK) hacia 'Libro': identifica qué libro fue prestado.
# - Clave foránea (FK) hacia 'Lector': identifica quién solicitó el préstamo.
# - 'devuelto': booleano clave para la regla de negocio (False = préstamo activo).
# - 'fecha_dev': fecha límite estipulada para la devolución.
# =============================================================================
class Prestamo(models.Model):
    fecha_dev = models.DateField(
        verbose_name="Fecha de Devolución",
        help_text="Fecha comprometida para la devolución del libro"
    )
    devuelto = models.BooleanField(
        default=False,
        verbose_name="Devuelto",
        help_text="Indica si el libro ya fue devuelto a la biblioteca (False = En préstamo activo)"
    )
    libro = models.ForeignKey(
        Libro,
        on_delete=models.CASCADE,
        related_name="prestamos",
        verbose_name="Libro",
        help_text="Referencia al libro prestado (FK)"
    )
    lector = models.ForeignKey(
        Lector,
        on_delete=models.CASCADE,
        related_name="prestamos",
        verbose_name="Lector",
        help_text="Referencia al lector que tiene el préstamo (FK)"
    )

    class Meta:
        verbose_name = "Préstamo"
        verbose_name_plural = "Préstamos"

    def __str__(self):
        estado = "Devuelto" if self.devuelto else "Pendiente"
        return f"Préstamo #{self.id} - {self.libro.titulo} -> {self.lector} ({estado})"
