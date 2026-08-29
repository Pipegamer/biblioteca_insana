/**
 * =============================================================================
 * CONTROLADOR PRINCIPAL DEL FRONTEND (script.js)
 * =============================================================================
 * Gestiona de forma reactiva:
 * 1. Panel del Administrador:
 *    - CRUD Completo del Catálogo de Libros (Crear, Editar, Eliminar, Precios, Portadas).
 *    - CRUD de Lectores:
 *      * Padrón de Lectores Activos con Borrado Lógico.
 *      * Apartado / Papelera de Lectores Desactivados con opción de REACTIVAR.
 * 2. Portal del Lector:
 *    - Catálogo con portadas y precios.
 *    - Gestión de préstamos y DEVOLUCIÓN en línea de libros.
 *    - Regla de morosidad y bloqueo de reservas.
 * =============================================================================
 */

// Endpoints de la API REST
const API_LECTORES_URL = '/api/lectores/';
const API_LIBROS_URL = '/api/libros/';
const API_PRESTAMOS_URL = '/api/prestamos/';
const API_MIS_PRESTAMOS_URL = '/api/prestamos/mis-prestamos/';
const API_SOLICITAR_PRESTAMO_URL = '/api/prestamos/solicitar/';

// Variables de estado global
let estadoMorosidadGlobal = false;
let catalogoLibrosGlobal = [];
let estadoLectoresGlobal = [];
let librosAdminGlobal = [];
let filtroEstadoLectorActual = 'activos'; // 'activos' | 'desactivados' | 'todos'

document.addEventListener('DOMContentLoaded', () => {
    // -------------------------------------------------------------------------
    // A. MODO ADMINISTRADOR (CRUD Libros + CRUD Lectores con Reactivación)
    // -------------------------------------------------------------------------
    const formRegistroLibro = document.getElementById('form-registro-libro');
    const formRegistroLector = document.getElementById('form-registro-lector');

    if (formRegistroLibro || formRegistroLector) {
        inicializarModuloAdmin();
    }

    // -------------------------------------------------------------------------
    // B. PORTAL DEL LECTOR (Catálogo + Préstamos + Devolución)
    // -------------------------------------------------------------------------
    const catalogoLibrosContainer = document.getElementById('libros-grid');
    const prestamosContainer = document.getElementById('prestamos-container');

    if (catalogoLibrosContainer || prestamosContainer) {
        inicializarModuloLector();
    }
});


// =============================================================================
// ==================== MÓDULO 1: PORTAL DEL LECTOR ============================
// =============================================================================

function inicializarModuloLector() {
    obtenerPrestamosLector().then(() => {
        obtenerCatalogoLibros();
    });

    const searchLibros = document.getElementById('input-search-libros');
    if (searchLibros) {
        searchLibros.addEventListener('input', filtrarCatalogoLibros);
    }

    const btnRefreshPrestamos = document.getElementById('btn-refresh-prestamos');
    if (btnRefreshPrestamos) {
        btnRefreshPrestamos.addEventListener('click', () => {
            obtenerPrestamosLector().then(() => obtenerCatalogoLibros());
        });
    }
}

/**
 * Consulta préstamos del lector autenticado, evalúa morosidad y renderiza tabla.
 */
async function obtenerPrestamosLector() {
    const loadingEl = document.getElementById('loading-prestamos');
    const tableWrapper = document.getElementById('prestamos-container');
    const emptyEl = document.getElementById('empty-prestamos');
    const tbody = document.getElementById('prestamos-tbody');
    const bannerMorosidad = document.getElementById('morosidad-banner');
    const statActivos = document.getElementById('stat-prestamos-activos');

    try {
        if (loadingEl) loadingEl.style.display = 'block';
        if (tableWrapper) tableWrapper.style.display = 'none';
        if (emptyEl) emptyEl.style.display = 'none';

        const res = await fetch(API_MIS_PRESTAMOS_URL, {
            headers: { 'Accept': 'application/json' }
        });

        if (!res.ok) throw new Error(`Error ${res.status} al consultar préstamos`);

        const data = await res.json();
        const prestamos = data.prestamos || [];
        estadoMorosidadGlobal = Boolean(data.tiene_morosidad);

        // Actualizar banner de morosidad
        if (bannerMorosidad) {
            bannerMorosidad.style.display = estadoMorosidadGlobal ? 'block' : 'none';
        }

        if (tbody) {
            tbody.innerHTML = '';
            let conteoActivos = 0;

            if (prestamos.length === 0) {
                if (emptyEl) emptyEl.style.display = 'block';
            } else {
                prestamos.forEach(p => {
                    if (!p.devuelto) conteoActivos++;

                    const tr = document.createElement('tr');
                    if (p.atrasado) tr.className = 'row-overdue';

                    const estadoBadge = p.devuelto
                        ? `<span class="badge-returned">✓ Devuelto</span>`
                        : (p.atrasado
                            ? `<span class="badge-overdue">⚠ Atrasado / Moroso</span>`
                            : `<span class="badge-ontime">● En Préstamo</span>`);

                    const situacionTexto = p.devuelto
                        ? '<span style="color:#64748B;">Completado</span>'
                        : (p.atrasado
                            ? '<strong style="color:#B91C1C;">Expirado - Entregar a la brevedad</strong>'
                            : '<span style="color:#1F7A54;">Dentro del plazo</span>');

                    const accionHtml = p.devuelto
                        ? '<span style="color:#94A3B8; font-size:0.82rem;">— Entregado —</span>'
                        : `<button class="btn-return-book" data-id="${p.id}" data-titulo="${escapeHTML(p.libro_titulo || 'Libro')}">
                               <span>📥</span> <span>Devolver Libro</span>
                           </button>`;

                    tr.innerHTML = `
                        <td><strong>#${String(p.id).padStart(3, '0')}</strong></td>
                        <td><strong>${escapeHTML(p.libro_titulo || 'Libro')}</strong></td>
                        <td><span class="badge-price-gold">${p.libro_precio || '$9.990 CLP'}</span></td>
                        <td>${escapeHTML(p.fecha_dev || 'Sin fecha')}</td>
                        <td>${estadoBadge}</td>
                        <td>${situacionTexto}</td>
                        <td style="text-align: center;">${accionHtml}</td>
                    `;

                    const btnDevolver = tr.querySelector('.btn-return-book');
                    if (btnDevolver) {
                        btnDevolver.addEventListener('click', () => {
                            ejecutarDevolucionLibro(p.id, p.libro_titulo || 'Libro');
                        });
                    }

                    tbody.appendChild(tr);
                });

                if (tableWrapper) tableWrapper.style.display = 'block';
            }

            if (statActivos) statActivos.textContent = conteoActivos;
        }

    } catch (err) {
        console.error('Error al cargar préstamos:', err);
        mostrarToast('Error al consultar préstamos del usuario', 'error');
    } finally {
        if (loadingEl) loadingEl.style.display = 'none';
    }
}

/**
 * Ejecuta la acción de devolver un libro (POST /api/prestamos/{id}/devolver/).
 */
async function ejecutarDevolucionLibro(prestamoId, tituloLibro) {
    const url = `${API_PRESTAMOS_URL}${prestamoId}/devolver/`;

    try {
        const csrfToken = getCSRFToken();

        const res = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });

        if (res.ok) {
            mostrarToast(`¡Gracias! Has devuelto "${tituloLibro}" a la biblioteca.`, 'success');
            await obtenerPrestamosLector();
            await obtenerCatalogoLibros();
        } else {
            const errData = await res.json();
            mostrarToast(errData.error || 'Error al procesar la devolución.', 'error');
        }
    } catch (err) {
        console.error('Error al devolver libro:', err);
        mostrarToast('Error de conexión al devolver el libro', 'error');
    }
}

/**
 * Consulta el catálogo de libros con sus portadas y precios para el lector.
 */
async function obtenerCatalogoLibros() {
    const loadingEl = document.getElementById('loading-libros');
    const gridEl = document.getElementById('libros-grid');
    const emptyEl = document.getElementById('empty-libros');
    const statLibros = document.getElementById('stat-libros-disponibles');

    try {
        if (loadingEl) loadingEl.style.display = 'block';
        if (gridEl) gridEl.style.display = 'none';
        if (emptyEl) emptyEl.style.display = 'none';

        const res = await fetch(API_LIBROS_URL, {
            headers: { 'Accept': 'application/json' }
        });

        if (!res.ok) throw new Error(`Error ${res.status} al consultar libros`);

        const data = await res.json();
        catalogoLibrosGlobal = Array.isArray(data) ? data : (data.results || []);

        if (statLibros) statLibros.textContent = catalogoLibrosGlobal.length;

        renderizarCatalogoLibros(catalogoLibrosGlobal);

    } catch (err) {
        console.error('Error al cargar catálogo de libros:', err);
        mostrarToast('Error al obtener el catálogo de libros', 'error');
    } finally {
        if (loadingEl) loadingEl.style.display = 'none';
    }
}

/**
 * Renderiza las tarjetas del catálogo con portada, precio y botón de solicitud.
 */
function renderizarCatalogoLibros(libros) {
    const gridEl = document.getElementById('libros-grid');
    const emptyEl = document.getElementById('empty-libros');
    if (!gridEl) return;

    gridEl.innerHTML = '';

    if (libros.length === 0) {
        if (emptyEl) emptyEl.style.display = 'block';
        return;
    }

    if (emptyEl) emptyEl.style.display = 'none';
    gridEl.style.display = 'grid';

    libros.forEach(libro => {
        const autoresNombres = (libro.autores_info && libro.autores_info.length > 0)
            ? libro.autores_info.map(a => a.nombre_autor).join(', ')
            : 'Autor no especificado';

        const editorialNombres = (libro.editoriales_info && libro.editoriales_info.length > 0)
            ? libro.editoriales_info.map(e => e.nombre_editorial).join(', ')
            : 'Editorial estándar';

        const precioTexto = libro.precio_formateado || `$${Number(libro.precio || 9990).toLocaleString('es-CL')} CLP`;

        const card = document.createElement('article');
        card.className = 'book-card';

        const portadaHtml = libro.imagen_url
            ? `<img src="${libro.imagen_url}" alt="${escapeHTML(libro.titulo)}" class="book-cover-img">`
            : `<div class="book-cover-placeholder-card">
                   <span class="ph-icon">📖</span>
                   <span class="ph-title">${escapeHTML(libro.titulo)}</span>
               </div>`;

        const botonBloqueado = estadoMorosidadGlobal;
        const textoBoton = botonBloqueado
            ? '🚫 Bloqueado por Morosidad'
            : '📖 Solicitar Préstamo';

        card.innerHTML = `
            <div class="book-card-cover-container">
                ${portadaHtml}
                <div class="book-card-price-tag">💰 ${precioTexto}</div>
            </div>
            <div class="book-card-top">
                <h3 class="book-title">${escapeHTML(libro.titulo)}</h3>
                <p class="book-authors"><strong>Autor(es):</strong> ${escapeHTML(autoresNombres)}</p>
                <p class="book-publishers"><strong>Editorial:</strong> ${escapeHTML(editorialNombres)}</p>
                <p class="book-description">${escapeHTML(libro.descripcion || 'Ejemplar disponible para préstamo académico.')}</p>
            </div>
            <div class="book-card-bottom">
                <button
                    class="btn-reserve"
                    data-id="${libro.id}"
                    data-titulo="${escapeHTML(libro.titulo)}"
                    ${botonBloqueado ? 'disabled' : ''}
                    title="${botonBloqueado ? 'No puedes solicitar libros debido a préstamos pendientes vencidos' : 'Reservar este libro'}"
                >
                    ${textoBoton}
                </button>
            </div>
        `;

        const btnReserva = card.querySelector('.btn-reserve');
        if (!botonBloqueado) {
            btnReserva.addEventListener('click', () => {
                solicitarPrestamoLibro(libro.id, libro.titulo);
            });
        }

        gridEl.appendChild(card);
    });
}

async function solicitarPrestamoLibro(libroId, libroTitulo) {
    if (estadoMorosidadGlobal) {
        mostrarToast('Acción bloqueada: Tienes préstamos atrasados.', 'error');
        return;
    }

    try {
        const csrfToken = getCSRFToken();

        const res = await fetch(API_SOLICITAR_PRESTAMO_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ libro_id: libroId })
        });

        if (res.status === 201) {
            mostrarToast(`¡Préstamo registrado! Has solicitado "${libroTitulo}".`, 'success');
            await obtenerPrestamosLector();
            await obtenerCatalogoLibros();
        } else {
            const errData = await res.json();
            const msg = errData.error || 'No fue posible solicitar el préstamo.';
            mostrarToast(msg, 'error');
        }
    } catch (err) {
        console.error('Error al solicitar préstamo:', err);
        mostrarToast('Error de conexión al solicitar préstamo', 'error');
    }
}

function filtrarCatalogoLibros(e) {
    const termino = e.target.value.toLowerCase().trim();
    if (!termino) {
        renderizarCatalogoLibros(catalogoLibrosGlobal);
        return;
    }

    const filtrados = catalogoLibrosGlobal.filter(libro => {
        const tituloMatch = libro.titulo.toLowerCase().includes(termino);
        const autorMatch = libro.autores_info && libro.autores_info.some(a => a.nombre_autor.toLowerCase().includes(termino));
        const editMatch = libro.editoriales_info && libro.editoriales_info.some(ed => ed.nombre_editorial.toLowerCase().includes(termino));
        return tituloMatch || autorMatch || editMatch;
    });

    renderizarCatalogoLibros(filtrados);
}


// =============================================================================
// ==================== MÓDULO 2: PANEL DE ADMINISTRACIÓN ======================
// =============================================================================

function inicializarModuloAdmin() {
    // 1. Carga inicial de datos
    obtenerLibrosAdmin();
    obtenerLectoresAdmin();

    // 2. Formulario de Creación de Libros (CRUD)
    const formLibro = document.getElementById('form-registro-libro');
    if (formLibro) {
        formLibro.addEventListener('submit', manejarRegistroLibroAdmin);
    }

    // 3. Formulario de Edición de Libros (Modal)
    const formEditarLibro = document.getElementById('form-editar-libro');
    if (formEditarLibro) {
        formEditarLibro.addEventListener('submit', manejarGuardarEdicionLibro);
    }

    const btnCancelarEdicion = document.getElementById('btn-cancelar-edicion-libro');
    if (btnCancelarEdicion) {
        btnCancelarEdicion.addEventListener('click', cerrarModalEdicionLibro);
    }

    // 4. Previsualizadores de Imagen (Creación y Edición)
    const inputImagen = document.getElementById('input-libro-imagen');
    if (inputImagen) {
        inputImagen.addEventListener('change', (e) => manejarPrevisualizacionImagen(e, 'image-preview', 'file-chosen-label'));
    }

    const editInputImagen = document.getElementById('edit-libro-imagen');
    if (editInputImagen) {
        editInputImagen.addEventListener('change', (e) => manejarPrevisualizacionImagen(e, 'edit-image-preview', 'edit-file-chosen-label'));
    }

    // 5. Búsqueda de Libros en Admin
    const searchLibrosAdmin = document.getElementById('input-search-libros-admin');
    if (searchLibrosAdmin) {
        searchLibrosAdmin.addEventListener('input', filtrarLibrosAdmin);
    }

    const btnRefreshLibros = document.getElementById('btn-refresh-libros-admin');
    if (btnRefreshLibros) {
        btnRefreshLibros.addEventListener('click', () => {
            mostrarCargaLibrosAdmin(true);
            obtenerLibrosAdmin();
        });
    }

    // 6. Formulario de Lectores
    const formLector = document.getElementById('form-registro-lector');
    if (formLector) {
        formLector.addEventListener('submit', manejarRegistroLectorAdmin);
    }

    const inputSearchLector = document.getElementById('input-search');
    if (inputSearchLector) {
        inputSearchLector.addEventListener('input', manejarBusquedaLectoresAdmin);
    }

    const btnRefreshLector = document.getElementById('btn-refresh');
    if (btnRefreshLector) {
        btnRefreshLector.addEventListener('click', () => {
            mostrarCargaAdmin(true);
            obtenerLectoresAdmin();
        });
    }

    // Modal de Alerta
    const btnModalClose = document.getElementById('btn-modal-close');
    if (btnModalClose) {
        btnModalClose.addEventListener('click', cerrarModalAlerta);
    }

    const modalAlert = document.getElementById('modal-alert');
    if (modalAlert) {
        modalAlert.addEventListener('click', (e) => {
            if (e.target === modalAlert) cerrarModalAlerta();
        });
    }

    const modalEditar = document.getElementById('modal-editar-libro');
    if (modalEditar) {
        modalEditar.addEventListener('click', (e) => {
            if (e.target === modalEditar) cerrarModalEdicionLibro();
        });
    }
}

/**
 * Cambio de pestaña principal en el panel administrativo (Libros vs Lectores).
 */
window.cambiarTabAdmin = function(tabName) {
    const seccionLibros = document.getElementById('seccion-libros');
    const seccionLectores = document.getElementById('seccion-lectores');
    const tabBtnLibros = document.getElementById('tab-btn-libros');
    const tabBtnLectores = document.getElementById('tab-btn-lectores');

    if (tabName === 'libros') {
        if (seccionLibros) seccionLibros.style.display = 'block';
        if (seccionLectores) seccionLectores.style.display = 'none';
        if (tabBtnLibros) tabBtnLibros.classList.add('active');
        if (tabBtnLectores) tabBtnLectores.classList.remove('active');
    } else {
        if (seccionLibros) seccionLibros.style.display = 'none';
        if (seccionLectores) seccionLectores.style.display = 'block';
        if (tabBtnLibros) tabBtnLibros.classList.remove('active');
        if (tabBtnLectores) tabBtnLectores.classList.add('active');
    }
};

/**
 * Filtro por estado de los lectores (Activos vs Desactivados / Papelera vs Todos).
 */
window.filtrarEstadoLectoresAdmin = function(filtro) {
    filtroEstadoLectorActual = filtro;

    const pillActivos = document.getElementById('pill-lectores-activos');
    const pillDesactivados = document.getElementById('pill-lectores-desactivados');
    const pillTodos = document.getElementById('pill-lectores-todos');

    if (pillActivos) pillActivos.classList.toggle('active', filtro === 'activos');
    if (pillDesactivados) pillDesactivados.classList.toggle('active', filtro === 'desactivados');
    if (pillTodos) pillTodos.classList.toggle('active', filtro === 'todos');

    aplicarFiltrosYRenderizarLectoresAdmin();
};

function manejarPrevisualizacionImagen(e, imgElementId, labelElementId) {
    const file = e.target.files[0];
    const previewImg = document.getElementById(imgElementId);
    const labelText = document.getElementById(labelElementId);

    if (file) {
        if (labelText) labelText.textContent = `Archivo: ${file.name}`;
        const reader = new FileReader();
        reader.onload = function(evt) {
            if (previewImg) {
                previewImg.src = evt.target.result;
                previewImg.style.display = 'block';
            }
        };
        reader.readAsDataURL(file);
    } else {
        if (labelText) labelText.textContent = 'Haz clic para seleccionar imagen de portada';
        if (previewImg) {
            previewImg.src = '';
            previewImg.style.display = 'none';
        }
    }
}

// -----------------------------------------------------------------------------
// GESTIÓN DE LIBROS (ADMINISTRADOR)
// -----------------------------------------------------------------------------
async function obtenerLibrosAdmin() {
    try {
        mostrarCargaLibrosAdmin(true);
        const res = await fetch(API_LIBROS_URL, {
            headers: { 'Accept': 'application/json' }
        });

        if (!res.ok) throw new Error(`Error ${res.status} al consultar libros`);

        const data = await res.json();
        librosAdminGlobal = Array.isArray(data) ? data : (data.results || []);

        renderizarLibrosAdmin(librosAdminGlobal);

        const counterEl = document.getElementById('total-libros-count');
        if (counterEl) counterEl.textContent = librosAdminGlobal.length;

    } catch (err) {
        console.error('Error al obtener libros admin:', err);
        mostrarToast('Error al conectar con la API de libros', 'error');
        mostrarEstadoVacioLibrosAdmin(true);
    } finally {
        mostrarCargaLibrosAdmin(false);
    }
}

function renderizarLibrosAdmin(lista) {
    const container = document.getElementById('libros-admin-list');
    if (!container) return;

    container.innerHTML = '';

    if (lista.length === 0) {
        mostrarEstadoVacioLibrosAdmin(true);
        return;
    }

    mostrarEstadoVacioLibrosAdmin(false);
    container.style.display = 'grid';

    lista.forEach(libro => {
        const autoresNombres = (libro.autores_info && libro.autores_info.length > 0)
            ? libro.autores_info.map(a => a.nombre_autor).join(', ')
            : 'Sin autor';

        const editorialNombres = (libro.editoriales_info && libro.editoriales_info.length > 0)
            ? libro.editoriales_info.map(e => e.nombre_editorial).join(', ')
            : 'Sin editorial';

        const precioTexto = libro.precio_formateado || `$${Number(libro.precio || 9990).toLocaleString('es-CL')} CLP`;

        const card = document.createElement('article');
        card.className = 'admin-book-item';
        card.id = `admin-book-item-${libro.id}`;

        const portadaHtml = libro.imagen_url
            ? `<img src="${libro.imagen_url}" alt="${escapeHTML(libro.titulo)}" class="admin-book-cover">`
            : `<div class="admin-book-placeholder">📖</div>`;

        card.innerHTML = `
            ${portadaHtml}
            <div class="admin-book-info">
                <h4 class="admin-book-title">${escapeHTML(libro.titulo)}</h4>
                <div class="admin-book-meta">
                    <span class="badge-price-gold">💰 ${precioTexto}</span>
                    <span><strong>Autor(es):</strong> ${escapeHTML(autoresNombres)}</span>
                    <span><strong>Editorial:</strong> ${escapeHTML(editorialNombres)}</span>
                </div>
            </div>
            <div class="admin-book-actions">
                <button class="btn-edit-academic" data-id="${libro.id}" title="Editar este libro">
                    <span>✏️</span> <span>Editar</span>
                </button>
                <button class="btn-delete-academic" data-id="${libro.id}" data-titulo="${escapeHTML(libro.titulo)}" title="Eliminar del catálogo">
                    <span>🗑️</span> <span>Eliminar</span>
                </button>
            </div>
        `;

        const btnEditar = card.querySelector('.btn-edit-academic');
        btnEditar.addEventListener('click', () => {
            abrirModalEdicionLibro(libro);
        });

        const btnEliminar = card.querySelector('.btn-delete-academic');
        btnEliminar.addEventListener('click', () => {
            ejecutarEliminacionLibroAdmin(libro.id, libro.titulo);
        });

        container.appendChild(card);
    });
}

function abrirModalEdicionLibro(libro) {
    const modal = document.getElementById('modal-editar-libro');
    if (!modal) return;

    document.getElementById('edit-libro-id').value = libro.id;
    document.getElementById('edit-libro-titulo').value = libro.titulo || '';
    document.getElementById('edit-libro-precio').value = libro.precio || 9990;

    const autoresNombres = (libro.autores_info && libro.autores_info.length > 0)
        ? libro.autores_info.map(a => a.nombre_autor).join(', ')
        : '';
    document.getElementById('edit-libro-autor').value = autoresNombres;

    const editorialNombres = (libro.editoriales_info && libro.editoriales_info.length > 0)
        ? libro.editoriales_info.map(e => e.nombre_editorial).join(', ')
        : '';
    document.getElementById('edit-libro-editorial').value = editorialNombres;

    document.getElementById('edit-libro-descripcion').value = libro.descripcion || '';

    const previewImg = document.getElementById('edit-image-preview');
    const labelText = document.getElementById('edit-file-chosen-label');
    if (libro.imagen_url && previewImg) {
        previewImg.src = libro.imagen_url;
        previewImg.style.display = 'block';
        if (labelText) labelText.textContent = 'Portada actual (selecciona otra para reemplazar)';
    } else if (previewImg) {
        previewImg.src = '';
        previewImg.style.display = 'none';
        if (labelText) labelText.textContent = 'Haz clic para seleccionar imagen de portada';
    }

    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
}

function cerrarModalEdicionLibro() {
    const modal = document.getElementById('modal-editar-libro');
    if (!modal) return;
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
}

async function manejarGuardarEdicionLibro(e) {
    e.preventDefault();

    const form = e.target;
    const libroId = document.getElementById('edit-libro-id').value;
    const formData = new FormData(form);
    const btnSubmit = document.getElementById('btn-submit-edicion-libro');

    const titulo = formData.get('titulo');
    const autorNombre = formData.get('autor_nombre');
    const editorialNombre = formData.get('editorial_nombre');

    if (!titulo || !autorNombre || !editorialNombre) {
        mostrarToast('Por favor completa los campos obligatorios (*)', 'error');
        return;
    }

    try {
        btnSubmit.disabled = true;
        btnSubmit.querySelector('.btn-text').textContent = 'Guardando cambios...';

        const csrfToken = getCSRFToken();

        const res = await fetch(`${API_LIBROS_URL}${libroId}/`, {
            method: 'PATCH',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        });

        if (res.ok) {
            const actualizado = await res.json();
            mostrarToast(`Libro "${actualizado.titulo}" actualizado exitosamente`, 'success');
            cerrarModalEdicionLibro();
            await obtenerLibrosAdmin();
        } else {
            const errData = await res.json();
            console.error('Error al actualizar libro:', errData);
            mostrarToast('Error al actualizar el libro en el catálogo', 'error');
        }
    } catch (err) {
        console.error('Error de conexión al editar libro:', err);
        mostrarToast('Error de conexión con el servidor', 'error');
    } finally {
        btnSubmit.disabled = false;
        btnSubmit.querySelector('.btn-text').textContent = 'Guardar Cambios';
    }
}

async function manejarRegistroLibroAdmin(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);
    const btnSubmit = document.getElementById('btn-submit-libro');

    const titulo = formData.get('titulo');
    const autorNombre = formData.get('autor_nombre');
    const editorialNombre = formData.get('editorial_nombre');

    if (!titulo || !autorNombre || !editorialNombre) {
        mostrarToast('Por favor completa los campos obligatorios del libro (*)', 'error');
        return;
    }

    try {
        btnSubmit.disabled = true;
        btnSubmit.querySelector('.btn-text').textContent = 'Guardando libro...';

        const csrfToken = getCSRFToken();

        const res = await fetch(API_LIBROS_URL, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        });

        if (res.status === 201) {
            const nuevo = await res.json();
            mostrarToast(`Libro "${nuevo.titulo}" agregado exitosamente al catálogo`, 'success');
            form.reset();

            const previewImg = document.getElementById('image-preview');
            const labelText = document.getElementById('file-chosen-label');
            if (previewImg) previewImg.style.display = 'none';
            if (labelText) labelText.textContent = 'Haz clic para seleccionar imagen de portada';

            await obtenerLibrosAdmin();
        } else {
            const errData = await res.json();
            mostrarToast('Error al registrar el libro en el catálogo', 'error');
        }
    } catch (err) {
        console.error('Error de conexión al crear libro:', err);
        mostrarToast('Error de conexión con el servidor', 'error');
    } finally {
        btnSubmit.disabled = false;
        btnSubmit.querySelector('.btn-text').textContent = 'Publicar Libro en Catálogo';
    }
}

async function ejecutarEliminacionLibroAdmin(libroId, libroTitulo) {
    const url = `${API_LIBROS_URL}${libroId}/`;

    try {
        const csrfToken = getCSRFToken();

        const res = await fetch(url, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });

        if (res.status === 204) {
            mostrarToast(`Libro "${libroTitulo}" eliminado del catálogo`, 'success');
            const item = document.getElementById(`admin-book-item-${libroId}`);
            if (item) {
                item.classList.add('fade-out');
                setTimeout(() => {
                    item.remove();
                    librosAdminGlobal = librosAdminGlobal.filter(l => l.id !== libroId);
                    const counterEl = document.getElementById('total-libros-count');
                    if (counterEl) counterEl.textContent = librosAdminGlobal.length;
                    if (librosAdminGlobal.length === 0) mostrarEstadoVacioLibrosAdmin(true);
                }, 300);
            }
        } else {
            mostrarToast('No se pudo eliminar el libro.', 'error');
        }
    } catch (err) {
        console.error('Error al eliminar libro:', err);
        mostrarToast('Error de conexión al eliminar libro', 'error');
    }
}

function filtrarLibrosAdmin(e) {
    const termino = e.target.value.toLowerCase().trim();
    if (!termino) {
        renderizarLibrosAdmin(librosAdminGlobal);
        return;
    }

    const filtrados = librosAdminGlobal.filter(libro => {
        const tituloMatch = libro.titulo.toLowerCase().includes(termino);
        const autorMatch = libro.autores_info && libro.autores_info.some(a => a.nombre_autor.toLowerCase().includes(termino));
        const editMatch = libro.editoriales_info && libro.editoriales_info.some(ed => ed.nombre_editorial.toLowerCase().includes(termino));
        return tituloMatch || autorMatch || editMatch;
    });

    renderizarLibrosAdmin(filtrados);
}

function mostrarCargaLibrosAdmin(mostrar) {
    const spinner = document.getElementById('loading-libros-admin');
    const list = document.getElementById('libros-admin-list');
    if (spinner) spinner.style.display = mostrar ? 'block' : 'none';
    if (mostrar && list) list.style.display = 'none';
}

function mostrarEstadoVacioLibrosAdmin(mostrar) {
    const empty = document.getElementById('empty-libros-admin');
    const list = document.getElementById('libros-admin-list');
    if (!empty) return;
    empty.style.display = mostrar ? 'block' : 'none';
    if (mostrar && list) list.style.display = 'none';
}

// -----------------------------------------------------------------------------
// GESTIÓN DE LECTORES (ADMINISTRADOR) - CRUD, BORRADO LÓGICO Y REACTIVACIÓN
// -----------------------------------------------------------------------------
async function obtenerLectoresAdmin() {
    try {
        mostrarCargaAdmin(true);
        const res = await fetch(API_LECTORES_URL, {
            headers: { 'Accept': 'application/json' }
        });

        if (!res.ok) throw new Error(`Error ${res.status} al consultar lectores`);

        const data = await res.json();
        estadoLectoresGlobal = Array.isArray(data) ? data : (data.results || []);

        actualizarContadoresLectores(estadoLectoresGlobal);
        aplicarFiltrosYRenderizarLectoresAdmin();

    } catch (err) {
        console.error('Error al obtener lectores:', err);
        mostrarToast('Error al conectar con la API de lectores', 'error');
        mostrarEstadoVacioAdmin(true, 'Ocurrió un error al cargar los datos.');
    } finally {
        mostrarCargaAdmin(false);
    }
}

function actualizarContadoresLectores(lista) {
    const activos = lista.filter(l => l.is_active).length;
    const desactivados = lista.filter(l => !l.is_active).length;
    const total = lista.length;

    const countActivos = document.getElementById('count-lectores-activos');
    const countDesactivados = document.getElementById('count-lectores-desactivados');
    const countTodos = document.getElementById('count-lectores-todos');
    const counterBadge = document.getElementById('total-count');

    if (countActivos) countActivos.textContent = activos;
    if (countDesactivados) countDesactivados.textContent = desactivados;
    if (countTodos) countTodos.textContent = total;
    if (counterBadge) counterBadge.textContent = total;
}

function aplicarFiltrosYRenderizarLectoresAdmin() {
    const inputSearch = document.getElementById('input-search');
    const termino = inputSearch ? inputSearch.value.toLowerCase().trim() : '';

    let filtrados = estadoLectoresGlobal;

    // Filtro por pestaña de estado
    if (filtroEstadoLectorActual === 'activos') {
        filtrados = filtrados.filter(l => l.is_active);
    } else if (filtroEstadoLectorActual === 'desactivados') {
        filtrados = filtrados.filter(l => !l.is_active);
    }

    // Filtro por término de búsqueda
    if (termino) {
        filtrados = filtrados.filter(lector => {
            const nombreCompleto = `${lector.nombres} ${lector.apellido_p} ${lector.apellido_m}`.toLowerCase();
            const rutMatch = (lector.rut || '').toLowerCase().includes(termino);
            const idMatch = String(lector.id).includes(termino);
            return nombreCompleto.includes(termino) || rutMatch || idMatch;
        });
    }

    renderizarLectoresAdmin(filtrados);
}

function renderizarLectoresAdmin(lista) {
    const container = document.getElementById('lectores-list');
    if (!container) return;

    container.innerHTML = '';

    if (lista.length === 0) {
        let emptyMsg = 'No se encontraron lectores registrados.';
        if (filtroEstadoLectorActual === 'desactivados') {
            emptyMsg = 'No hay lectores desactivados en este momento. Todos se encuentran activos.';
        } else if (filtroEstadoLectorActual === 'activos') {
            emptyMsg = 'No hay lectores activos.';
        }
        mostrarEstadoVacioAdmin(true, emptyMsg);
        return;
    }

    mostrarEstadoVacioAdmin(false);
    container.style.display = 'grid';

    lista.forEach(lector => {
        const nombreCompleto = `${lector.nombres} ${lector.apellido_p} ${lector.apellido_m}`;
        const iniciales = `${lector.nombres.charAt(0)}${lector.apellido_p.charAt(0)}`.toUpperCase();
        const idFormateado = String(lector.id).padStart(3, '0');
        const estaActivo = lector.is_active;

        const card = document.createElement('article');
        card.className = `lector-card ${estaActivo ? 'active' : 'inactive'}`;
        card.id = `lector-card-${lector.id}`;

        const accionBtnHtml = estaActivo
            ? `<button class="btn-delete-academic" data-id="${lector.id}" data-name="${escapeHTML(nombreCompleto)}" title="Desactivar lector (Borrado Lógico)">
                   <span class="btn-del-icon">🗑️</span>
                   <span>Desactivar</span>
               </button>`
            : `<button class="btn-reactivate-academic" data-id="${lector.id}" data-name="${escapeHTML(nombreCompleto)}" title="Reactivar cuenta de lector">
                   <span>🔄</span>
                   <span>Reactivar Lector</span>
               </button>`;

        card.innerHTML = `
            <div class="lector-info-section">
                <div class="avatar-seal" title="Iniciales del lector">${iniciales}</div>
                <div class="lector-details">
                    <h3 class="lector-full-name">${escapeHTML(nombreCompleto)}</h3>
                    <div class="lector-meta">
                        <span class="badge-id">ID: #${idFormateado}</span>
                        ${lector.rut ? `<span class="badge-id">RUT: ${escapeHTML(lector.rut)}</span>` : ''}
                        <span class="badge-status ${estaActivo ? 'active' : 'inactive'}">
                            ${estaActivo ? '● Activo' : '○ Desactivado (Borrado Lógico)'}
                        </span>
                    </div>
                </div>
            </div>
            <div class="lector-action-section">
                ${accionBtnHtml}
            </div>
        `;

        if (estaActivo) {
            const btnEliminar = card.querySelector('.btn-delete-academic');
            btnEliminar.addEventListener('click', () => {
                ejecutarEliminacionLectorAdmin(lector.id, nombreCompleto);
            });
        } else {
            const btnReactivar = card.querySelector('.btn-reactivate-academic');
            btnReactivar.addEventListener('click', () => {
                ejecutarReactivacionLectorAdmin(lector.id, nombreCompleto);
            });
        }

        container.appendChild(card);
    });
}

async function manejarRegistroLectorAdmin(e) {
    e.preventDefault();

    const inputRut = document.getElementById('input-rut');
    const inputNombres = document.getElementById('input-nombres');
    const inputApellidoP = document.getElementById('input-apellido-p');
    const inputApellidoM = document.getElementById('input-apellido-m');
    const btnSubmit = document.getElementById('btn-submit-lector');

    const payload = {
        rut: inputRut ? inputRut.value.trim() : '',
        nombres: inputNombres.value.trim(),
        apellido_p: inputApellidoP.value.trim(),
        apellido_m: inputApellidoM.value.trim(),
        is_active: true
    };

    if (!payload.nombres || !payload.apellido_p || !payload.apellido_m) {
        mostrarToast('Por favor completa todos los campos requeridos (*)', 'error');
        return;
    }

    try {
        btnSubmit.disabled = true;
        btnSubmit.querySelector('.btn-text').textContent = 'Guardando...';

        const csrfToken = getCSRFToken();

        const res = await fetch(API_LECTORES_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        });

        if (res.status === 201) {
            const nuevo = await res.json();
            mostrarToast(`Lector ${nuevo.nombres} ${nuevo.apellido_p} registrado exitosamente`, 'success');
            e.target.reset();
            inputNombres.focus();
            await obtenerLectoresAdmin();
        } else {
            const errData = await res.json();
            mostrarToast('Error al registrar lector en la base de datos', 'error');
        }
    } catch (err) {
        console.error('Error al registrar lector:', err);
        mostrarToast('Error de conexión con el servidor', 'error');
    } finally {
        btnSubmit.disabled = false;
        btnSubmit.querySelector('.btn-text').textContent = 'Registrar Lector';
    }
}

/**
 * Borrado Lógico: Desactiva un lector (is_active = False) si no tiene préstamos activos.
 */
async function ejecutarEliminacionLectorAdmin(id, nombreCompleto) {
    const url = `${API_LECTORES_URL}${id}/`;

    try {
        const csrfToken = getCSRFToken();
        const res = await fetch(url, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });

        if (res.status === 204) {
            mostrarToast(`Lector "${nombreCompleto}" desactivado (movido a Desactivados)`, 'success');
            // Actualizar estado local
            const lector = estadoLectoresGlobal.find(l => l.id === id);
            if (lector) lector.is_active = false;

            actualizarContadoresLectores(estadoLectoresGlobal);
            aplicarFiltrosYRenderizarLectoresAdmin();
            return;
        }

        if (res.status === 400) {
            const errData = await res.json();
            const msg = errData.error || 'No se puede eliminar el usuario porque tiene libros sin devolver.';
            abrirModalAlerta({
                titulo: 'Acción Bloqueada por Regla de Negocio',
                mensaje: msg,
                nombreLector: nombreCompleto
            });
            return;
        }

        mostrarToast(`Respuesta no esperada del servidor: ${res.status}`, 'error');

    } catch (err) {
        console.error('Error al desactivar lector:', err);
        mostrarToast('Error de red al intentar desactivar el lector', 'error');
    }
}

/**
 * Reactivación: Restaura un lector previamente desactivado (is_active = True).
 */
async function ejecutarReactivacionLectorAdmin(id, nombreCompleto) {
    const url = `${API_LECTORES_URL}${id}/reactivar/`;

    try {
        const csrfToken = getCSRFToken();
        const res = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });

        if (res.ok) {
            mostrarToast(`¡Lector "${nombreCompleto}" reactivado exitosamente!`, 'success');
            const lector = estadoLectoresGlobal.find(l => l.id === id);
            if (lector) lector.is_active = true;

            actualizarContadoresLectores(estadoLectoresGlobal);
            aplicarFiltrosYRenderizarLectoresAdmin();
        } else {
            const errData = await res.json();
            mostrarToast(errData.error || 'No se pudo reactivar el lector.', 'error');
        }
    } catch (err) {
        console.error('Error al reactivar lector:', err);
        mostrarToast('Error de red al intentar reactivar el lector', 'error');
    }
}

function manejarBusquedaLectoresAdmin() {
    aplicarFiltrosYRenderizarLectoresAdmin();
}

function mostrarCargaAdmin(mostrar) {
    const spinner = document.getElementById('loading-spinner');
    const list = document.getElementById('lectores-list');
    if (spinner) spinner.style.display = mostrar ? 'block' : 'none';
    if (mostrar && list) list.style.display = 'none';
}

function mostrarEstadoVacioAdmin(mostrar, msg = null) {
    const empty = document.getElementById('empty-state');
    const list = document.getElementById('lectores-list');
    if (!empty) return;
    empty.style.display = mostrar ? 'block' : 'none';
    if (mostrar && list) list.style.display = 'none';
    if (msg) {
        const p = empty.querySelector('p');
        if (p) p.textContent = msg;
    }
}

function abrirModalAlerta({ titulo, mensaje, nombreLector }) {
    const modal = document.getElementById('modal-alert');
    const modalTitle = document.getElementById('modal-alert-title');
    const modalMsg = document.getElementById('modal-alert-message');
    if (!modal) return;

    if (modalTitle) modalTitle.textContent = titulo;
    if (modalMsg) {
        modalMsg.innerHTML = `<strong>${escapeHTML(nombreLector)}</strong><br>${escapeHTML(mensaje)}`;
    }

    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
}

function cerrarModalAlerta() {
    const modal = document.getElementById('modal-alert');
    if (!modal) return;
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
}

// -----------------------------------------------------------------------------
// UTILIDADES
// -----------------------------------------------------------------------------
function mostrarToast(mensaje, tipo = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${tipo}`;
    const icono = tipo === 'success' ? '✅' : tipo === 'error' ? '⚠️' : 'ℹ️';
    toast.innerHTML = `<span>${icono}</span> <span>${escapeHTML(mensaje)}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function getCSRFToken() {
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    if (input) return input.value;
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}

function escapeHTML(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
