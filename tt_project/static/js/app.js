// Global State
let allProducts = [];
let dashboardStats = null;
let currentStatusFilter = 'all';
let currentCategoryFilter = 'all';
let searchQuery = '';
let activeTab = 'inventory';

let categoryValueChartInstance = null;
let categoryUnitsChartInstance = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    setupEventListeners();
    await Promise.all([
        loadStats(),
        loadCategories(),
        loadProducts(),
        loadLowStockAlerts()
    ]);
}

function setupEventListeners() {
    // Search input with debounce
    const searchInput = document.getElementById('search-input');
    let debounceTimer;
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                searchQuery = e.target.value.trim();
                loadProducts();
            }, 250);
        });
    }

    // Category filter dropdown
    const categoryFilter = document.getElementById('category-filter');
    if (categoryFilter) {
        categoryFilter.addEventListener('change', (e) => {
            currentCategoryFilter = e.target.value;
            loadProducts();
        });
    }

    // Dynamic adjustment form radio changes
    const movementRadios = document.querySelectorAll('input[name="movement_type"]');
    movementRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            const label = document.getElementById('adjust-qty-label');
            const qtyInput = document.getElementById('adjust-quantity');
            if (e.target.value === 'IN') {
                label.innerHTML = 'Quantity to Add <span class="text-red-500">*</span>';
                qtyInput.min = "1";
            } else if (e.target.value === 'OUT') {
                label.innerHTML = 'Quantity to Deduct <span class="text-red-500">*</span>';
                qtyInput.min = "1";
            } else {
                label.innerHTML = 'New Exact Count <span class="text-red-500">*</span>';
                qtyInput.min = "0";
            }
        });
    });
}

// ==================== DATA FETCHING ====================

async function loadProducts() {
    const tableBody = document.getElementById('product-table-body');
    const showingCount = document.getElementById('showing-count');

    try {
        let url = `/api/products?status=${encodeURIComponent(currentStatusFilter)}`;
        if (currentCategoryFilter && currentCategoryFilter !== 'all') {
            url += `&category=${encodeURIComponent(currentCategoryFilter)}`;
        }
        if (searchQuery) {
            url += `&search=${encodeURIComponent(searchQuery)}`;
        }

        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to fetch products');
        allProducts = await res.json();

        if (showingCount) showingCount.textContent = allProducts.length;

        renderProductTable(allProducts);
    } catch (err) {
        console.error(err);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-5 py-8 text-center text-red-500">
                        <i class="fa-solid fa-circle-exclamation text-xl mb-1"></i>
                        <p>Error loading products: ${err.message}</p>
                    </td>
                </tr>
            `;
        }
    }
}

async function loadStats() {
    try {
        const res = await fetch('/api/inventory/stats');
        if (!res.ok) throw new Error('Failed to fetch inventory statistics');
        dashboardStats = await res.json();

        // Update KPI metrics
        document.getElementById('stat-total-products').textContent = dashboardStats.total_products.toLocaleString();
        document.getElementById('stat-total-units').textContent = dashboardStats.total_stock_units.toLocaleString();
        document.getElementById('stat-total-value').textContent = '$' + dashboardStats.total_inventory_value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
        document.getElementById('stat-low-stock').textContent = dashboardStats.low_stock_count;
        document.getElementById('stat-out-of-stock').textContent = dashboardStats.out_of_stock_count;

        // Update charts if on analytics tab
        if (activeTab === 'analytics') {
            renderCharts(dashboardStats);
            renderCategorySummaryTable(dashboardStats.category_breakdown);
        }
    } catch (err) {
        console.error('Error loading stats:', err);
    }
}

async function loadCategories() {
    try {
        const res = await fetch('/api/categories');
        if (!res.ok) throw new Error('Failed to fetch categories');
        const categories = await res.json();

        const catSelect = document.getElementById('category-filter');
        const catDatalist = document.getElementById('category-datalist');

        if (catSelect) {
            catSelect.innerHTML = '<option value="all">All Categories</option>';
            categories.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c;
                opt.textContent = c;
                catSelect.appendChild(opt);
            });
        }

        if (catDatalist) {
            catDatalist.innerHTML = '';
            categories.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c;
                catDatalist.appendChild(opt);
            });
        }
    } catch (err) {
        console.error('Error loading categories:', err);
    }
}

async function loadLowStockAlerts() {
    try {
        const res = await fetch('/api/inventory/low-stock');
        if (!res.ok) throw new Error('Failed to fetch low stock alerts');
        const lowStockItems = await res.json();

        const badgeDot = document.getElementById('low-stock-badge-dot');
        const badgeCount = document.getElementById('low-stock-badge-count');
        const banner = document.getElementById('low-stock-banner');
        const bannerItems = document.getElementById('low-stock-banner-items');

        if (lowStockItems.length > 0) {
            if (badgeDot) badgeDot.classList.remove('hidden');
            if (badgeCount) {
                badgeCount.textContent = lowStockItems.length;
                badgeCount.classList.remove('hidden');
            }

            if (banner && bannerItems) {
                banner.classList.remove('hidden');
                bannerItems.innerHTML = lowStockItems.map(item => `
                    <button onclick="openAdjustModal(${item.id})" class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-white border border-amber-300 text-amber-800 hover:bg-amber-100 transition-colors">
                        <span>${escapeHtml(item.name)} (${item.quantity} ${item.unit})</span>
                        <i class="fa-solid fa-plus text-[10px] text-amber-600"></i>
                    </button>
                `).join('');
            }
        } else {
            if (badgeDot) badgeDot.classList.add('hidden');
            if (badgeCount) badgeCount.classList.add('hidden');
            if (banner) banner.classList.add('hidden');
        }
    } catch (err) {
        console.error('Error checking alerts:', err);
    }
}

async function loadMovements() {
    const tableBody = document.getElementById('movements-table-body');
    if (!tableBody) return;

    tableBody.innerHTML = `
        <tr>
            <td colspan="6" class="px-5 py-8 text-center text-slate-400">
                <i class="fa-solid fa-spinner fa-spin text-lg mb-1"></i>
                <p>Loading audit movements...</p>
            </td>
        </tr>
    `;

    try {
        const res = await fetch('/api/inventory/movements?limit=40');
        if (!res.ok) throw new Error('Failed to fetch movements');
        const movements = await res.json();

        if (movements.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="px-5 py-8 text-center text-slate-400">
                        No recorded stock movements yet.
                    </td>
                </tr>
            `;
            return;
        }

        tableBody.innerHTML = movements.map(m => {
            const date = new Date(m.timestamp).toLocaleString();
            let typeBadge = '';
            let changeFormatted = '';

            if (m.movement_type === 'IN') {
                typeBadge = '<span class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200"><i class="fa-solid fa-arrow-down mr-1"></i>Restock</span>';
                changeFormatted = `<span class="font-bold text-emerald-600">+${m.quantity_change}</span>`;
            } else if (m.movement_type === 'OUT') {
                typeBadge = '<span class="px-2 py-0.5 rounded text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200"><i class="fa-solid fa-arrow-up mr-1"></i>Dispatch</span>';
                changeFormatted = `<span class="font-bold text-rose-600">${m.quantity_change}</span>`;
            } else {
                typeBadge = '<span class="px-2 py-0.5 rounded text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200"><i class="fa-solid fa-sliders mr-1"></i>Audit</span>';
                changeFormatted = `<span class="font-bold text-blue-600">${m.quantity_change >= 0 ? '+' : ''}${m.quantity_change}</span>`;
            }

            return `
                <tr class="hover:bg-slate-50/60 transition-colors">
                    <td class="px-5 py-3 text-xs text-slate-500 whitespace-nowrap">${date}</td>
                    <td class="px-5 py-3">
                        <div class="font-semibold text-slate-900">${escapeHtml(m.product_name || 'Product #' + m.product_id)}</div>
                        <div class="text-[11px] font-mono text-slate-400">${escapeHtml(m.product_sku || '')}</div>
                    </td>
                    <td class="px-5 py-3">${typeBadge}</td>
                    <td class="px-5 py-3">${changeFormatted}</td>
                    <td class="px-5 py-3 text-xs">
                        <span class="text-slate-400">${m.previous_quantity}</span>
                        <i class="fa-solid fa-arrow-right text-[10px] text-slate-300 mx-1.5"></i>
                        <span class="font-semibold text-slate-800">${m.new_quantity}</span>
                    </td>
                    <td class="px-5 py-3 text-xs text-slate-500 max-w-xs truncate">${escapeHtml(m.reason || '—')}</td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="px-5 py-8 text-center text-red-500">
                    Failed to load movements: ${err.message}
                </td>
            </tr>
        `;
    }
}

// ==================== TABLE RENDERING ====================

function renderProductTable(products) {
    const tableBody = document.getElementById('product-table-body');
    if (!tableBody) return;

    if (products.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="px-5 py-12 text-center text-slate-400">
                    <div class="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-3 text-slate-400">
                        <i class="fa-solid fa-magnifying-glass text-lg"></i>
                    </div>
                    <p class="font-medium text-slate-600">No matching products found</p>
                    <p class="text-xs text-slate-400 mt-1">Try adjusting your search criteria or add a new product</p>
                </td>
            </tr>
        `;
        return;
    }

    tableBody.innerHTML = products.map(p => {
        // Status Badge Logic
        let statusBadge = '';
        let stockBarColor = 'bg-emerald-500';
        const percent = Math.min(100, Math.round((p.quantity / Math.max(p.min_threshold * 2, 1)) * 100));

        if (p.quantity <= 0) {
            statusBadge = `
                <span class="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold badge-out-stock">
                    <span class="w-1.5 h-1.5 rounded-full bg-red-600"></span>
                    <span>Out of Stock</span>
                </span>
            `;
            stockBarColor = 'bg-red-500';
        } else if (p.quantity <= p.min_threshold) {
            statusBadge = `
                <span class="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold badge-low-stock">
                    <i class="fa-solid fa-triangle-exclamation text-[10px]"></i>
                    <span>Low Stock (≤ ${p.min_threshold})</span>
                </span>
            `;
            stockBarColor = 'bg-amber-500';
        } else {
            statusBadge = `
                <span class="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold badge-in-stock">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
                    <span>In Stock</span>
                </span>
            `;
        }

        return `
            <tr class="hover:bg-slate-50/80 transition-colors">
                <!-- SKU & Name -->
                <td class="px-5 py-3.5">
                    <div class="font-mono text-xs font-semibold text-indigo-600">${escapeHtml(p.sku)}</div>
                    <div class="font-medium text-slate-900">${escapeHtml(p.name)}</div>
                    ${p.description ? `<div class="text-xs text-slate-400 truncate max-w-xs mt-0.5">${escapeHtml(p.description)}</div>` : ''}
                </td>

                <!-- Category -->
                <td class="px-5 py-3.5">
                    <span class="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                        ${escapeHtml(p.category)}
                    </span>
                </td>

                <!-- Pricing -->
                <td class="px-5 py-3.5">
                    <div class="font-semibold text-slate-900">$${p.price.toFixed(2)}</div>
                    <div class="text-xs text-slate-400">Cost: $${p.cost_price.toFixed(2)}</div>
                </td>

                <!-- Stock Level & Threshold -->
                <td class="px-5 py-3.5">
                    <div class="flex items-center justify-between mb-1.5">
                        <span class="text-sm font-bold ${p.quantity <= p.min_threshold ? (p.quantity <= 0 ? 'text-red-600' : 'text-amber-600') : 'text-slate-800'}">
                            ${p.quantity} <span class="text-xs font-normal text-slate-500">${escapeHtml(p.unit)}</span>
                        </span>
                        <span class="text-xs text-slate-400">Min: ${p.min_threshold}</span>
                    </div>
                    <div class="stock-bar-bg">
                        <div class="stock-bar-fill ${stockBarColor}" style="width: ${percent}%;"></div>
                    </div>
                </td>

                <!-- Status -->
                <td class="px-5 py-3.5">
                    ${statusBadge}
                </td>

                <!-- Actions -->
                <td class="px-5 py-3.5 text-right whitespace-nowrap space-x-1">
                    <button onclick="openAdjustModal(${p.id})" title="Adjust Stock (Restock/Dispatch)" class="p-1.5 text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors">
                        <i class="fa-solid fa-arrow-right-arrow-left text-sm"></i>
                    </button>
                    <button onclick="openEditProductModal(${p.id})" title="Edit Product Details" class="p-1.5 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                        <i class="fa-solid fa-pen-to-square text-sm"></i>
                    </button>
                    <button onclick="openDeleteModal(${p.id})" title="Delete Product" class="p-1.5 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                        <i class="fa-solid fa-trash-can text-sm"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// ==================== TABS & FILTERS ====================

function switchTab(tab) {
    activeTab = tab;

    const tabBtnInv = document.getElementById('tab-inventory');
    const tabBtnMov = document.getElementById('tab-movements');
    const tabBtnAna = document.getElementById('tab-analytics');

    const viewInv = document.getElementById('view-inventory');
    const viewMov = document.getElementById('view-movements');
    const viewAna = document.getElementById('view-analytics');

    // Reset tab button states
    [tabBtnInv, tabBtnMov, tabBtnAna].forEach(btn => {
        btn.classList.remove('border-indigo-600', 'text-indigo-600');
        btn.classList.add('border-transparent', 'text-slate-500');
    });

    // Hide all views
    [viewInv, viewMov, viewAna].forEach(view => view.classList.add('hidden'));

    if (tab === 'inventory') {
        tabBtnInv.classList.add('border-indigo-600', 'text-indigo-600');
        tabBtnInv.classList.remove('border-transparent', 'text-slate-500');
        viewInv.classList.remove('hidden');
        loadProducts();
    } else if (tab === 'movements') {
        tabBtnMov.classList.add('border-indigo-600', 'text-indigo-600');
        tabBtnMov.classList.remove('border-transparent', 'text-slate-500');
        viewMov.classList.remove('hidden');
        loadMovements();
    } else if (tab === 'analytics') {
        tabBtnAna.classList.add('border-indigo-600', 'text-indigo-600');
        tabBtnAna.classList.remove('border-transparent', 'text-slate-500');
        viewAna.classList.remove('hidden');
        if (dashboardStats) {
            renderCharts(dashboardStats);
            renderCategorySummaryTable(dashboardStats.category_breakdown);
        } else {
            loadStats();
        }
    }
}

function filterByStatus(status) {
    currentStatusFilter = status;

    // Switch to inventory tab if not already on it
    if (activeTab !== 'inventory') {
        switchTab('inventory');
    }

    const buttons = ['all', 'in_stock', 'low_stock', 'out_of_stock']; // 'needs_restock' (bell) has no button
    buttons.forEach(b => {
        const btn = document.getElementById(`filter-status-${b}`);
        if (!btn) return;
        if (b === status) {
            btn.className = 'px-2.5 py-1.5 rounded-md bg-white text-indigo-700 font-bold shadow-sm transition-all';
        } else {
            btn.className = 'px-2.5 py-1.5 rounded-md text-slate-600 hover:text-slate-900 transition-all';
        }
    });

    loadProducts();
}

function resetFilters() {
    searchQuery = '';
    currentCategoryFilter = 'all';
    currentStatusFilter = 'all';

    const searchInput = document.getElementById('search-input');
    if (searchInput) searchInput.value = '';

    const catSelect = document.getElementById('category-filter');
    if (catSelect) catSelect.value = 'all';

    filterByStatus('all');
}

function dismissBanner() {
    const banner = document.getElementById('low-stock-banner');
    if (banner) banner.classList.add('hidden');
}

// ==================== MODAL ACTIONS ====================

function openModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
}

function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
}

function openAddProductModal() {
    const form = document.getElementById('add-product-form');
    if (form) form.reset();
    openModal('add-modal');
}

async function handleAddProduct(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    const payload = {
        sku: formData.get('sku'),
        name: formData.get('name'),
        category: formData.get('category'),
        description: formData.get('description') || null,
        price: parseFloat(formData.get('price')),
        cost_price: parseFloat(formData.get('cost_price') || 0),
        quantity: parseInt(formData.get('quantity'), 10),
        min_threshold: parseInt(formData.get('min_threshold'), 10),
        unit: formData.get('unit') || 'pcs'
    };

    try {
        const res = await fetch('/api/products', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to create product');

        closeModal('add-modal');
        showToast(`Product "${payload.name}" added successfully!`, 'success');
        await Promise.all([loadProducts(), loadStats(), loadCategories(), loadLowStockAlerts()]);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function openEditProductModal(id) {
    const prod = allProducts.find(p => p.id === id);
    if (!prod) return;

    document.getElementById('edit-product-id').value = prod.id;
    document.getElementById('edit-sku').value = prod.sku;
    document.getElementById('edit-category').value = prod.category;
    document.getElementById('edit-name').value = prod.name;
    document.getElementById('edit-description').value = prod.description || '';
    document.getElementById('edit-price').value = prod.price;
    document.getElementById('edit-cost-price').value = prod.cost_price;
    document.getElementById('edit-min-threshold').value = prod.min_threshold;
    document.getElementById('edit-unit').value = prod.unit;

    openModal('edit-modal');
}

async function handleEditProduct(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const id = formData.get('id');

    const payload = {
        sku: formData.get('sku'),
        name: formData.get('name'),
        category: formData.get('category'),
        description: formData.get('description') || null,
        price: parseFloat(formData.get('price')),
        cost_price: parseFloat(formData.get('cost_price') || 0),
        min_threshold: parseInt(formData.get('min_threshold'), 10),
        unit: formData.get('unit') || 'pcs'
    };

    try {
        const res = await fetch(`/api/products/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to update product');

        closeModal('edit-modal');
        showToast(`Product "${payload.name}" updated successfully!`, 'success');
        await Promise.all([loadProducts(), loadStats(), loadCategories(), loadLowStockAlerts()]);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function openAdjustModal(id) {
    const prod = allProducts.find(p => p.id === id);
    if (!prod) return;

    document.getElementById('adjust-product-id').value = prod.id;
    document.getElementById('adjust-prod-name').textContent = prod.name;
    document.getElementById('adjust-prod-sku').textContent = prod.sku;
    document.getElementById('adjust-prod-qty').textContent = `${prod.quantity} ${prod.unit}`;

    const form = document.getElementById('adjust-stock-form');
    form.reset();

    // Default to 'IN' (Restock)
    const inRadio = form.querySelector('input[value="IN"]');
    if (inRadio) inRadio.checked = true;
    document.getElementById('adjust-qty-label').innerHTML = 'Quantity to Add <span class="text-red-500">*</span>';
    document.getElementById('adjust-quantity').min = "1";

    openModal('adjust-modal');
}

async function handleStockAdjust(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const id = formData.get('product_id');

    const payload = {
        movement_type: formData.get('movement_type'),
        quantity: parseInt(formData.get('quantity'), 10),
        reason: formData.get('reason') || null
    };

    try {
        const res = await fetch(`/api/products/${id}/adjust-stock`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Stock adjustment failed');

        closeModal('adjust-modal');
        showToast(`Stock updated! New quantity: ${data.quantity} ${data.unit}`, 'success');
        await Promise.all([loadProducts(), loadStats(), loadLowStockAlerts()]);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function openDeleteModal(id) {
    const prod = allProducts.find(p => p.id === id);
    document.getElementById('delete-prod-name').textContent = prod ? prod.name : `#${id}`;
    const btn = document.getElementById('confirm-delete-btn');
    btn.onclick = () => confirmDelete(id);
    openModal('delete-modal');
}

async function confirmDelete(id) {
    try {
        const res = await fetch(`/api/products/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to delete product');

        closeModal('delete-modal');
        showToast('Product deleted from inventory', 'info');
        await Promise.all([loadProducts(), loadStats(), loadCategories(), loadLowStockAlerts()]);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==================== CHARTS & ANALYTICS ====================

function renderCharts(stats) {
    if (!stats || !stats.category_breakdown) return;

    const categories = stats.category_breakdown.map(c => c.category);
    const values = stats.category_breakdown.map(c => c.total_value);
    const units = stats.category_breakdown.map(c => c.total_quantity);

    const colors = [
        '#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ec4899',
        '#8b5cf6', '#3b82f6', '#14b8a6', '#84cc16', '#f97316'
    ];

    // Destroy existing instances if any
    if (categoryValueChartInstance) categoryValueChartInstance.destroy();
    if (categoryUnitsChartInstance) categoryUnitsChartInstance.destroy();

    // 1. Doughnut Chart: Asset Valuation
    const ctxVal = document.getElementById('categoryValueChart');
    if (ctxVal) {
        categoryValueChartInstance = new Chart(ctxVal, {
            type: 'doughnut',
            data: {
                labels: categories,
                datasets: [{
                    data: values,
                    backgroundColor: colors.slice(0, categories.length),
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` $${context.raw.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
                            }
                        }
                    }
                }
            }
        });
    }

    // 2. Bar Chart: Physical Units
    const ctxUnits = document.getElementById('categoryUnitsChart');
    if (ctxUnits) {
        categoryUnitsChartInstance = new Chart(ctxUnits, {
            type: 'bar',
            data: {
                labels: categories,
                datasets: [{
                    label: 'Units in Stock',
                    data: units,
                    backgroundColor: '#6366f1',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }
}

function renderCategorySummaryTable(breakdown) {
    const tbody = document.getElementById('category-summary-body');
    if (!tbody || !breakdown) return;

    tbody.innerHTML = breakdown.map(cat => `
        <tr class="hover:bg-slate-50 transition-colors">
            <td class="px-6 py-3 font-semibold text-slate-800">${escapeHtml(cat.category)}</td>
            <td class="px-6 py-3 text-slate-600">${cat.product_count} items</td>
            <td class="px-6 py-3 text-slate-600 font-medium">${cat.total_quantity.toLocaleString()} units</td>
            <td class="px-6 py-3 font-bold text-slate-900">$${cat.total_value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
        </tr>
    `).join('');
}

// ==================== TOAST SYSTEM ====================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast bg-white border rounded-xl shadow-lg p-3 text-xs flex items-center space-x-2.5 max-w-sm';

    let icon = '';
    if (type === 'success') {
        toast.classList.add('border-emerald-200');
        icon = '<i class="fa-solid fa-circle-check text-emerald-500 text-sm"></i>';
    } else if (type === 'error') {
        toast.classList.add('border-red-200');
        icon = '<i class="fa-solid fa-circle-xmark text-red-500 text-sm"></i>';
    } else if (type === 'warning') {
        toast.classList.add('border-amber-200');
        icon = '<i class="fa-solid fa-triangle-exclamation text-amber-500 text-sm"></i>';
    } else {
        toast.classList.add('border-slate-200');
        icon = '<i class="fa-solid fa-circle-info text-blue-500 text-sm"></i>';
    }

    toast.innerHTML = `
        ${icon}
        <span class="text-slate-700 flex-1">${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Helper to escape HTML and prevent XSS
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
