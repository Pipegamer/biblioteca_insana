"""
=============================================================================
SCRIPT DE POBLADO DE BASE DE DATOS (SEED DATA) - seed_db.py
=============================================================================
Este script automatiza la inserción de datos de prueba relacionales en SQLite.
Permite validar:
1. La estructura en Tercera Forma Normal (3NF) y relaciones N:M de Libros/Autores/Editoriales.
2. Cuentas de usuario de Django segregadas por roles:
   - Administrador (superusuario): admin / admin1234
   - Lector regular: juan (RUT 12.345.678-9) / juan1234
   - Lector con morosidad: carlos (RUT 15.987.654-3) / carlos1234 (préstamo vencido)
   - Lectora sin préstamos: ana (RUT 18.765.432-1) / ana1234
3. Regla de morosidad (bloqueo de reservas si fecha_dev < hoy).
4. Regla de borrado lógico y bloqueo de eliminación de lectores con préstamos activos.
=============================================================================
"""

import os
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biblioteca.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import Lector, Autor, Editorial, Libro, Prestamo


def seed_database():
    print("=" * 60)
    print(" INICIANDO POBLADO DE BASE DE DATOS (seed_db.py)")
    print("=" * 60)

    # -------------------------------------------------------------------------
    # 1. SUPERUSUARIO (ADMINISTRACIÓN)
    # -------------------------------------------------------------------------
    username_admin = 'admin'
    password_admin = 'admin1234'
    email_admin = 'admin@biblioteca.local'

    user_admin, created_admin = User.objects.get_or_create(username=username_admin)
    if created_admin:
        user_admin.set_password(password_admin)
        user_admin.is_superuser = True
        user_admin.is_staff = True
        user_admin.email = email_admin
        user_admin.save()
        print(f"[+] Superusuario '{username_admin}' creado exitosamente (Pass: '{password_admin}').")
    else:
        user_admin.set_password(password_admin)
        user_admin.is_superuser = True
        user_admin.is_staff = True
        user_admin.save()
        print(f"[*] Superusuario '{username_admin}' actualizado en la base de datos.")

    # -------------------------------------------------------------------------
    # 2. AUTORES Y EDITORIALES (3NF)
    # -------------------------------------------------------------------------
    autor1, _ = Autor.objects.get_or_create(nombre_autor='Frank Herbert')
    autor2, _ = Autor.objects.get_or_create(nombre_autor='Gabriel García Márquez')
    autor3, _ = Autor.objects.get_or_create(nombre_autor='J.R.R. Tolkien')
    autor4, _ = Autor.objects.get_or_create(nombre_autor='Isaac Asimov')
    autor5, _ = Autor.objects.get_or_create(nombre_autor='Miguel de Cervantes')

    edit1, _ = Editorial.objects.get_or_create(nombre_editorial='McGraw Hill')
    edit2, _ = Editorial.objects.get_or_create(nombre_editorial='Editorial Sudamericana')
    edit3, _ = Editorial.objects.get_or_create(nombre_editorial='Minotauro')
    edit4, _ = Editorial.objects.get_or_create(nombre_editorial='Debolsillo')
    edit5, _ = Editorial.objects.get_or_create(nombre_editorial='Alianza Editorial')

    # -------------------------------------------------------------------------
    # 3. CATÁLOGO DE LIBROS (RELACIONES N:M)
    # -------------------------------------------------------------------------
    libros_data = [
        ("Duna", "Obra maestra de la ciencia ficción en el planeta desértico Arrakis.", 14990, autor1, edit1),
        ("Cien Años de Soledad", "Historia de la familia Buendía en el pueblo mítico de Macondo.", 12990, autor2, edit2),
        ("El Hobbit", "Las aventuras de Bilbo Bolsón en la Tierra Media.", 9990, autor3, edit3),
        ("Fundación", "La caída y reconstrucción del Imperio Galáctico mediante la psicohistoria.", 8990, autor4, edit4),
        ("Don Quijote de la Mancha", "El ingenioso hidalgo Don Quijote y su fiel escudero Sancho Panza.", 15990, autor5, edit5),
    ]

    libros_creados = []
    for titulo, desc, precio, aut, ed in libros_data:
        libro_obj, _ = Libro.objects.get_or_create(
            titulo=titulo,
            defaults={'descripcion': desc, 'precio': precio}
        )
        libro_obj.precio = precio
        libro_obj.descripcion = desc
        libro_obj.save()
        libro_obj.autores.add(aut)
        libro_obj.editoriales.add(ed)
        libros_creados.append(libro_obj)
        print(f"[+] Libro en catálogo: '{libro_obj.titulo}' - Precio: ${precio:,} CLP".replace(',', '.'))

    # -------------------------------------------------------------------------
    # 4. CREACIÓN DE LECTORES CON CUENTAS DE USUARIO DE DJANGO
    # -------------------------------------------------------------------------
    usuarios_lectores = [
        {
            'username': 'juan',
            'rut': '12.345.678-9',
            'nombres': 'Juan',
            'apellido_p': 'Pérez',
            'apellido_m': 'Gómez',
            'password': 'juan1234'
        },
        {
            'username': 'ana',
            'rut': '18.765.432-1',
            'nombres': 'Ana',
            'apellido_p': 'Ríos',
            'apellido_m': 'Soto',
            'password': 'ana1234'
        },
        {
            'username': 'carlos',
            'rut': '15.987.654-3',
            'nombres': 'Carlos',
            'apellido_p': 'Mendoza',
            'apellido_m': 'Silva',
            'password': 'carlos1234'
        }
    ]

    lectores_creados = {}
    for udata in usuarios_lectores:
        u_obj, _ = User.objects.get_or_create(username=udata['username'])
        u_obj.set_password(udata['password'])
        u_obj.first_name = udata['nombres']
        u_obj.last_name = f"{udata['apellido_p']} {udata['apellido_m']}"
        u_obj.save()

        lector_obj, _ = Lector.objects.get_or_create(
            rut=udata['rut'],
            defaults={
                'user': u_obj,
                'nombres': udata['nombres'],
                'apellido_p': udata['apellido_p'],
                'apellido_m': udata['apellido_m'],
                'is_active': True
            }
        )
        lector_obj.user = u_obj
        lector_obj.nombres = udata['nombres']
        lector_obj.apellido_p = udata['apellido_p']
        lector_obj.apellido_m = udata['apellido_m']
        lector_obj.is_active = True
        lector_obj.save()

        lectores_creados[udata['username']] = lector_obj
        print(f"[+] Cuenta Lector: {lector_obj} (Usuario: '{udata['username']}' | RUT: '{udata['rut']}' | Pass: '{udata['password']}')")

    # -------------------------------------------------------------------------
    # 5. PRÉSTAMOS DE PRUEBA (NORMAL Y CON MOROSIDAD)
    # -------------------------------------------------------------------------
    # Caso A: Juan tiene un préstamo ACTIVO AL DÍA (devolución en 5 días) -> bloquea borrado de Juan
    lector_juan = lectores_creados['juan']
    libro_duna = libros_creados[0]
    prestamo_juan, _ = Prestamo.objects.get_or_create(
        libro=libro_duna,
        lector=lector_juan,
        devuelto=False,
        defaults={'fecha_dev': date.today() + timedelta(days=5)}
    )
    print(f"[+] Préstamo activo al día: '{libro_duna.titulo}' para {lector_juan} (Devolución: {prestamo_juan.fecha_dev})")

    # Caso B: Carlos tiene un préstamo ATRASADO/MOROSO (venció hace 3 días) -> activa el banner rojo de morosidad
    lector_carlos = lectores_creados['carlos']
    libro_cien = libros_creados[1]
    prestamo_carlos, _ = Prestamo.objects.get_or_create(
        libro=libro_cien,
        lector=lector_carlos,
        devuelto=False,
        defaults={'fecha_dev': date.today() - timedelta(days=3)}
    )
    # Asegurar que esté vencido
    prestamo_carlos.fecha_dev = date.today() - timedelta(days=3)
    prestamo_carlos.devuelto = False
    prestamo_carlos.save()
    print(f"[!] Préstamo MOROSO / ATRASADO: '{libro_cien.titulo}' para {lector_carlos} (Venció: {prestamo_carlos.fecha_dev})")

    print("=" * 60)
    print(" BASE DE DATOS POBLADA EXITOSAMENTE CON ROLES Y DATOS DE PRUEBA")
    print("=" * 60)


if __name__ == '__main__':
    seed_database()
