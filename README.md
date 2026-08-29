# 🏛️ Sistema de Gestión de Biblioteca Central

Sistema web académico de gestión bibliográfica desarrollado con **Django 5**, **Django REST Framework (DRF)** y frontend interactivo en **Vanilla JavaScript & CSS**. Diseñado bajo principios de **Tercera Forma Normal (3NF)** y arquitectura desacoplada basada en API REST.

---

## 🌟 Características Principales

### 1. Modelo Relacional en 3NF
- **`Lector`**: Campos atómicos (`nombres`, `apellido_p`, `apellido_m`), RUT, usuario Django vinculado y campo booleano `is_active` para borrado lógico.
- **`Autor`**: Normalizado de forma atómica (`nombre_autor`).
- **`Editorial`**: Normalizado de forma atómica (`nombre_editorial`).
- **`Libro`**: Título, precio en pesos chilenos (`precio`), portada multimedia (`imagen`), sinopsis, y relaciones `ManyToManyField` nativas hacia `Autor` y `Editorial`.
- **`Prestamo`**: Tabla transaccional puente con clave foránea a `Libro` y `Lector`, fecha de devolución (`fecha_dev`) y estado de devolución (`devuelto`).

### 2. Reglas de Negocio Implementadas
- **Borrado Lógico y Protección de Préstamos Activos**: Si un lector posee libros sin devolver (`devuelto = False`), la API bloquea su eliminación retornando `HTTP 400 Bad Request`. Si no tiene deudas pendientes, se aplica borrado lógico (`is_active = False`).
- **Apartado de Lectores Desactivados y Reactivación**: Los lectores borrados lógicamente se organizan en un apartado especial y pueden ser reactivados en un clic (`POST /api/lectores/{id}/reactivar/`).
- **Regla de Morosidad en Reservas**: Si un usuario tiene al menos un préstamo vencido (`fecha_dev < hoy` y `devuelto = False`), el sistema activa un banner rojo de alerta permanente y bloquea la solicitud de nuevos préstamos.
- **Devolución de Libros en Línea**: Tanto el lector como el administrador pueden registrar devoluciones (`POST /api/prestamos/{id}/devolver/`), liberando de inmediato cualquier bloqueo por morosidad.
- **CRUD Completo del Catálogo de Libros**: Registro, edición con modal interactivo, asignación de precios y subida de imágenes de portada desde la computadora (`ImageField` + `Pillow`).

### 3. Separación de Roles y Vistas
- **Pantalla de Inicio Dual (`/`)**: Formulario lado a lado para acceso de **Lector** (RUT/ID) y **Administrador** (Superusuario).
- **Panel de Control de Administrador (`/dashboard-admin/`)**:
  - Pestaña de Catálogo de Libros (Creación, edición con modal, subida de archivos y eliminación).
  - Pestaña de Padrón de Lectores (Registro, filtros por estado: Activos vs Desactivados, y botón de reactivación).
- **Portal del Lector (`/mi-biblioteca/`)**:
  - Catálogo de libros con portadas ilustrativas y precios.
  - Tabla de préstamos personales con botón para devolver libros en tiempo real.

---

## 🛠️ Requisitos Previos

- **Python 3.10+**
- **Git**
- **Virtualenv**

---

## 🚀 Instalación y Puesta en Marcha

1. **Clonar el Repositorio:**
   ```bash
   git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
   cd TU_REPOSITORIO
   ```

2. **Crear y Activar el Entorno Virtual:**
   - En Windows:
     ```bash
     python -m venv env
     .\env\Scripts\activate
     ```
   - En Linux/macOS:
     ```bash
     python3 -m venv env
     source env/bin/activate
     ```

3. **Instalar Dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Aplicar Migraciones:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Poblar la Base de Datos con Datos de Prueba:**
   ```bash
   python seed_db.py
   ```

6. **Iniciar el Servidor de Desarrollo:**
   ```bash
   python manage.py runserver
   ```
   Accede a la plataforma en [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## 🔑 Credenciales de Acceso (Datos de Prueba)

| Rol | Usuario / RUT | Contraseña | URL de Acceso |
| :--- | :--- | :--- | :--- |
| **Administrador** | `admin` | `admin1234` | [http://127.0.0.1:8000/dashboard-admin/](http://127.0.0.1:8000/dashboard-admin/) |
| **Lector (Al día)** | `juan` *(RUT: 12.345.678-9)* | `juan1234` | [http://127.0.0.1:8000/mi-biblioteca/](http://127.0.0.1:8000/mi-biblioteca/) |
| **Lector (Al día)** | `ana` *(RUT: 18.765.432-1)* | `ana1234` | [http://127.0.0.1:8000/mi-biblioteca/](http://127.0.0.1:8000/mi-biblioteca/) |
| **Lector (Moroso)** | `carlos` *(RUT: 15.987.654-3)* | `carlos1234` | [http://127.0.0.1:8000/mi-biblioteca/](http://127.0.0.1:8000/mi-biblioteca/) |

---

## 🧪 Ejecución de Pruebas Automatizadas

El proyecto incluye 12 pruebas unitarias y de integración que validan endpoints REST, autenticación y reglas de negocio:

```bash
python manage.py test
```

---

## 📄 Licencia

Proyecto desarrollado con fines académicos y demostrativos.
