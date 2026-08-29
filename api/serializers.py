from datetime import date
from rest_framework import serializers
from .models import Lector, Autor, Editorial, Libro, Prestamo

# =============================================================================
# SERIALIZADORES (ModelSerializer)
# =============================================================================
# Los serializadores convierten los objetos del ORM de Django (instancias de modelos)
# a tipos de datos nativos de Python que luego se renderizan fácilmente en JSON/XML,
# y viceversa (deserialización y validación de datos entrantes desde requests HTTP).
# =============================================================================


# -----------------------------------------------------------------------------
# Serializador: Lector
# -----------------------------------------------------------------------------
# Transforma el modelo Lector en JSON.
# Incluye campos atómicos (nombres, apellido_p, apellido_m), RUT y el estado is_active.
class LectorSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Lector
        fields = '__all__'

    def get_nombre_completo(self, obj):
        return f"{obj.nombres} {obj.apellido_p} {obj.apellido_m}".strip()


# -----------------------------------------------------------------------------
# Serializador: Autor
# -----------------------------------------------------------------------------
# Expone los datos del autor para consumo y gestión en los endpoints de la API.
class AutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Autor
        fields = '__all__'


# -----------------------------------------------------------------------------
# Serializador: Editorial
# -----------------------------------------------------------------------------
# Expone la información de las editoriales en formato JSON.
class EditorialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Editorial
        fields = '__all__'


# -----------------------------------------------------------------------------
# Serializador: Libro
# -----------------------------------------------------------------------------
# Serializa el libro, incluyendo precio, imagen de portada, información de autores
# y editoriales (relaciones ManyToMany 3NF).
class LibroSerializer(serializers.ModelSerializer):
    autores = serializers.PrimaryKeyRelatedField(many=True, queryset=Autor.objects.all(), required=False)
    editoriales = serializers.PrimaryKeyRelatedField(many=True, queryset=Editorial.objects.all(), required=False)
    autores_info = AutorSerializer(source='autores', many=True, read_only=True)
    editoriales_info = EditorialSerializer(source='editoriales', many=True, read_only=True)
    imagen_url = serializers.SerializerMethodField(read_only=True)
    precio_formateado = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Libro
        fields = '__all__'

    def get_imagen_url(self, obj):
        request = self.context.get('request')
        if obj.imagen:
            if request is not None:
                return request.build_absolute_uri(obj.imagen.url)
            return obj.imagen.url
        return None

    def get_precio_formateado(self, obj):
        if obj.precio is not None:
            # Formato de moneda chilena / estándar ($X.XXX CLP)
            val = int(obj.precio)
            return f"${val:,.0f} CLP".replace(',', '.')
        return "$0 CLP"


# -----------------------------------------------------------------------------
# Serializador: Prestamo
# -----------------------------------------------------------------------------
# Serializa las transacciones de préstamos, vinculando las FK de Libro y Lector,
# así como la fecha de devolución y el estado booleano 'devuelto'.
# Provee además el cálculo dinámico de si el préstamo se encuentra atrasado (moroso).
class PrestamoSerializer(serializers.ModelSerializer):
    libro_titulo = serializers.CharField(source='libro.titulo', read_only=True)
    libro_precio = serializers.SerializerMethodField(read_only=True)
    lector_nombre = serializers.CharField(source='lector.__str__', read_only=True)
    atrasado = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Prestamo
        fields = '__all__'

    def get_libro_precio(self, obj):
        if obj.libro and obj.libro.precio is not None:
            val = int(obj.libro.precio)
            return f"${val:,.0f} CLP".replace(',', '.')
        return "$0 CLP"

    def get_atrasado(self, obj):
        """
        Regla de morosidad: True si el libro no ha sido devuelto y la fecha límite ya expiró.
        """
        if not obj.devuelto and obj.fecha_dev:
            return obj.fecha_dev < date.today()
        return False
