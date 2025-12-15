/**
 * Web Scraper Dashboard - JavaScript Principal
 * ============================================
 * Maneja toda la interactividad del dashboard
 */

// Configuración
const API_BASE_URL = 'http://localhost:8000/api';
const REFRESH_INTERVAL = 60000; // 1 minuto

// Estado de la aplicación
const state = {
    products: [],
    websites: [],
    logs: [],
    stats: {},
    currentPage: 1,
    totalPages: 1,
    pageSize: 20,
    filters: {
        website_id: '',
        search: '',
        sort_by: 'last_scraped',
        sort_order: 'desc'
    },
    selectedProduct: null,
    priceChart: null
};

// ============================================
// Utilidades
// ============================================

/**
 * Realiza una petición a la API
 */
async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error en la solicitud');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

/**
 * Formatea un precio en CLP
 */
function formatPrice(price) {
    if (!price) return '$0';
    return new Intl.NumberFormat('es-CL', {
        style: 'currency',
        currency: 'CLP',
        minimumFractionDigits: 0
    }).format(price);
}

/**
 * Formatea una fecha
 */
function formatDate(dateString) {
    if (!dateString) return '--';
    const date = new Date(dateString);
    return date.toLocaleDateString('es-CL', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Formatea una fecha relativa
 */
function formatRelativeDate(dateString) {
    if (!dateString) return '--';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Hace un momento';
    if (diffMins < 60) return `Hace ${diffMins} min`;
    if (diffHours < 24) return `Hace ${diffHours} hora${diffHours > 1 ? 's' : ''}`;
    if (diffDays < 7) return `Hace ${diffDays} día${diffDays > 1 ? 's' : ''}`;
    return formatDate(dateString);
}

/**
 * Muestra una notificación toast
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    }[type] || 'fa-info-circle';

    toast.innerHTML = `<i class="fas ${icon}"></i> ${message}`;
    container.appendChild(toast);

    // Auto-remove después de 4 segundos
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

/**
 * Muestra/oculta el overlay de carga
 */
function toggleLoading(show) {
    document.getElementById('loading-overlay').classList.toggle('hidden', !show);
}

// ============================================
// Carga de Datos
// ============================================

/**
 * Carga las estadísticas generales
 */
async function loadStats() {
    try {
        const stats = await apiRequest('/stats');
        state.stats = stats;

        document.getElementById('stat-total-products').textContent = stats.total_products;
        document.getElementById('stat-websites').textContent = stats.active_websites;
        document.getElementById('stat-high-discount').textContent = stats.products_high_discount;
        document.getElementById('stat-last-scraping').textContent = formatRelativeDate(stats.last_scraping);

    } catch (error) {
        console.error('Error cargando estadísticas:', error);
    }
}

/**
 * Carga los sitios web para el filtro
 */
async function loadWebsites() {
    try {
        const websites = await apiRequest('/websites');
        state.websites = websites;

        const select = document.getElementById('filter-website');
        select.innerHTML = '<option value="">Todos los sitios</option>';

        websites.forEach(website => {
            const option = document.createElement('option');
            option.value = website.id;
            option.textContent = `${website.name} (${website.products_count})`;
            select.appendChild(option);
        });

    } catch (error) {
        console.error('Error cargando sitios:', error);
    }
}

/**
 * Carga los productos con filtros y paginación
 */
async function loadProducts() {
    try {
        const params = new URLSearchParams({
            page: state.currentPage,
            page_size: state.pageSize,
            sort_by: state.filters.sort_by,
            sort_order: state.filters.sort_order
        });

        if (state.filters.website_id) {
            params.append('website_id', state.filters.website_id);
        }
        if (state.filters.search) {
            params.append('search', state.filters.search);
        }

        const data = await apiRequest(`/products?${params}`);
        state.products = data.items;
        state.totalPages = data.total_pages;

        renderProducts();
        updatePagination();

    } catch (error) {
        console.error('Error cargando productos:', error);
        document.getElementById('products-tbody').innerHTML = `
            <tr><td colspan="6" class="loading-cell">
                <i class="fas fa-exclamation-circle"></i> Error cargando productos
            </td></tr>
        `;
    }
}

/**
 * Carga los logs de scraping
 */
async function loadLogs() {
    try {
        const logs = await apiRequest('/scraping-logs?limit=20');
        state.logs = logs;
        renderLogs();

    } catch (error) {
        console.error('Error cargando logs:', error);
    }
}

/**
 * Carga el histórico de precios de un producto
 */
async function loadPriceHistory(productId) {
    try {
        const data = await apiRequest(`/products/${productId}/history?days=30`);
        state.selectedProduct = {
            id: productId,
            name: data.product_name,
            history: data.items
        };
        renderPriceChart();

    } catch (error) {
        console.error('Error cargando histórico:', error);
        showToast('Error cargando histórico de precios', 'error');
    }
}

// ============================================
// Renderizado
// ============================================

/**
 * Renderiza la tabla de productos
 */
function renderProducts() {
    const tbody = document.getElementById('products-tbody');

    if (!state.products.length) {
        tbody.innerHTML = `
            <tr><td colspan="6" class="loading-cell">
                <i class="fas fa-box-open"></i> No se encontraron productos
            </td></tr>
        `;
        return;
    }

    tbody.innerHTML = state.products.map(product => {
        const discountClass = product.discount >= 20 ? 'discount-high' :
                              product.discount >= 10 ? 'discount-medium' : 'discount-low';

        const priceChangedClass = product.price_changed ? 'price-changed' : '';

        return `
            <tr class="${priceChangedClass}" data-product-id="${product.id}">
                <td class="product-name">
                    <a href="${product.url}" target="_blank" title="${product.name}">
                        ${product.name}
                    </a>
                </td>
                <td>${product.website_name || 'N/A'}</td>
                <td class="price">
                    ${formatPrice(product.current_price)}
                    ${product.original_price && product.original_price > product.current_price ?
                        `<span class="original-price">${formatPrice(product.original_price)}</span>` : ''}
                </td>
                <td>
                    <span class="discount-badge ${discountClass}">
                        ${product.discount > 0 ? `-${product.discount.toFixed(0)}%` : '0%'}
                    </span>
                </td>
                <td class="date-cell">${formatRelativeDate(product.last_scraped)}</td>
                <td>
                    <button class="action-btn btn-view-history" data-id="${product.id}" title="Ver histórico">
                        <i class="fas fa-chart-line"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    // Agregar event listeners
    tbody.querySelectorAll('.btn-view-history').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const productId = btn.dataset.id;
            loadPriceHistory(productId);
        });
    });
}

/**
 * Renderiza los logs de scraping
 */
function renderLogs() {
    const container = document.getElementById('logs-container');

    if (!state.logs.length) {
        container.innerHTML = `
            <div class="log-item">
                <i class="fas fa-info-circle"></i> No hay logs disponibles
            </div>
        `;
        return;
    }

    container.innerHTML = state.logs.map(log => `
        <div class="log-item">
            <div class="log-header">
                <span class="log-website">${log.website_name || 'Sitio'}</span>
                <span class="log-status ${log.status}">${log.status}</span>
            </div>
            <div class="log-details">
                ${log.products_found} encontrados, ${log.products_new} nuevos, ${log.products_updated} actualizados
            </div>
            <div class="log-time">${formatDate(log.started_at)}</div>
        </div>
    `).join('');
}

/**
 * Renderiza el gráfico de precios
 */
function renderPriceChart() {
    const canvas = document.getElementById('price-chart');
    const placeholder = document.getElementById('chart-placeholder');
    const productInfo = document.getElementById('selected-product-info');

    if (!state.selectedProduct || !state.selectedProduct.history.length) {
        if (state.priceChart) {
            state.priceChart.destroy();
            state.priceChart = null;
        }
        placeholder.classList.remove('hidden');
        productInfo.classList.add('hidden');
        return;
    }

    placeholder.classList.add('hidden');
    productInfo.classList.remove('hidden');

    // Actualizar info del producto
    document.getElementById('selected-product-name').textContent = state.selectedProduct.name;
    const lastPrice = state.selectedProduct.history[state.selectedProduct.history.length - 1];
    document.getElementById('selected-product-price').textContent = formatPrice(lastPrice?.price || 0);

    // Preparar datos
    const labels = state.selectedProduct.history.map(h => {
        const date = new Date(h.scraped_at);
        return date.toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit' });
    });

    const prices = state.selectedProduct.history.map(h => h.price);

    // Destruir gráfico anterior
    if (state.priceChart) {
        state.priceChart.destroy();
    }

    // Crear nuevo gráfico
    state.priceChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Precio',
                data: prices,
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 4,
                pointBackgroundColor: '#3498db'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return formatPrice(context.raw);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return formatPrice(value);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Actualiza los controles de paginación
 */
function updatePagination() {
    const prevBtn = document.getElementById('btn-prev-page');
    const nextBtn = document.getElementById('btn-next-page');
    const pageInfo = document.getElementById('page-info');

    prevBtn.disabled = state.currentPage <= 1;
    nextBtn.disabled = state.currentPage >= state.totalPages;
    pageInfo.textContent = `Página ${state.currentPage} de ${state.totalPages || 1}`;
}

// ============================================
// Acciones
// ============================================

/**
 * Ejecuta scraping manual
 */
async function runManualScraping() {
    try {
        toggleLoading(true);
        showToast('Ejecutando scraping...', 'info');

        const result = await apiRequest('/scrape/manual', {
            method: 'POST',
            body: JSON.stringify({ website_id: null })
        });

        showToast(
            `Scraping completado: ${result.total_products_found} productos encontrados`,
            'success'
        );

        // Recargar datos
        await Promise.all([loadStats(), loadProducts(), loadLogs()]);

    } catch (error) {
        showToast(`Error en scraping: ${error.message}`, 'error');
    } finally {
        toggleLoading(false);
    }
}

/**
 * Aplica los filtros de búsqueda
 */
function applyFilters() {
    state.currentPage = 1;
    loadProducts();
}

// ============================================
// Event Listeners
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Cargar datos iniciales
    loadStats();
    loadWebsites();
    loadProducts();
    loadLogs();

    // Botón de scraping manual
    document.getElementById('btn-scrape-now').addEventListener('click', runManualScraping);

    // Filtro por sitio
    document.getElementById('filter-website').addEventListener('change', (e) => {
        state.filters.website_id = e.target.value;
        applyFilters();
    });

    // Búsqueda por nombre
    let searchTimeout;
    document.getElementById('filter-search').addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            state.filters.search = e.target.value;
            applyFilters();
        }, 300);
    });

    // Ordenamiento
    document.getElementById('filter-sort').addEventListener('change', (e) => {
        const [sort_by, sort_order] = e.target.value.split('-');
        state.filters.sort_by = sort_by;
        state.filters.sort_order = sort_order;
        applyFilters();
    });

    // Paginación
    document.getElementById('btn-prev-page').addEventListener('click', () => {
        if (state.currentPage > 1) {
            state.currentPage--;
            loadProducts();
        }
    });

    document.getElementById('btn-next-page').addEventListener('click', () => {
        if (state.currentPage < state.totalPages) {
            state.currentPage++;
            loadProducts();
        }
    });

    // Refrescar logs
    document.getElementById('btn-refresh-logs').addEventListener('click', loadLogs);

    // Modal
    document.getElementById('modal-close').addEventListener('click', () => {
        document.getElementById('modal-product').classList.add('hidden');
    });

    document.getElementById('modal-product').addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.classList.add('hidden');
        }
    });

    // Refrescar automáticamente cada minuto
    setInterval(() => {
        loadStats();
        loadLogs();
    }, REFRESH_INTERVAL);
});

// Exportar funciones para uso global si es necesario
window.loadPriceHistory = loadPriceHistory;
window.runManualScraping = runManualScraping;
