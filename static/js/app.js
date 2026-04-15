/**
 * Main Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

function initApp() {
    checkAuth();
    setupNavigation();
    setupLogin();
    setupLogout();
    setupConnectionListener();
    setupSystemMonitoring();
    setupOfflineQueueUI();
    setupPendingQueueProtection();
    setupResponsiveMenu();

    // Listen for auth changes
    window.addEventListener('auth-change', () => {
        checkAuth();
    });

    // Initial view
    if (api.isAuthenticated()) {
        renderView('dashboard');
    }
}

function setupSystemMonitoring() {
    const runCheck = async () => {
        if (!api.isAuthenticated()) return;
        try {
            const health = await api.getSystemHealth();
            if (health.status !== 'ok') {
                showToast('Atenção: existem pendências de migração no banco. Execute "python manage.py migrate".', 'warning');
            }
        } catch (error) {
            const message = String(error?.message || '');
            if (message.includes('Falha de estrutura do banco')) {
                showToast(message, 'error');
            }
        }
    };
    runCheck();
    setInterval(runCheck, 60000);
}

function checkAuth() {
    const loginScreen = document.getElementById('login-screen');
    const mainScreen = document.getElementById('main-screen');

    if (api.isAuthenticated()) {
        loginScreen.classList.add('hidden');
        mainScreen.classList.remove('hidden');
        document.getElementById('user-display-name').textContent = localStorage.getItem('username') || 'Usuário';
    } else {
        loginScreen.classList.remove('hidden');
        mainScreen.classList.add('hidden');
    }
}

function setupLogin() {
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            await api.login(username, password);
            loginError.classList.add('hidden');
            window.dispatchEvent(new CustomEvent('auth-change'));
            renderView('dashboard');
        } catch (error) {
            loginError.textContent = error.message || 'Erro ao fazer login. Verifique suas credenciais.';
            loginError.classList.remove('hidden');
        }
    });
}

function setupLogout() {
    document.getElementById('logout-btn').addEventListener('click', () => {
        api.logout();
    });
}

function setupConnectionListener() {
    const statusDiv = document.getElementById('connection-status');
    const updateStatus = () => {
        if (navigator.onLine) {
            statusDiv.className = 'flex items-center gap-2 px-3 py-1 rounded-full bg-green-50 text-green-600 text-xs font-bold';
            statusDiv.innerHTML = '<div class="w-2 h-2 rounded-full bg-green-500"></div><span>Online</span>';
            api.syncOfflineData();
        } else {
            statusDiv.className = 'flex items-center gap-2 px-3 py-1 rounded-full bg-red-50 text-red-600 text-xs font-bold';
            statusDiv.innerHTML = '<div class="w-2 h-2 rounded-full bg-red-500"></div><span>Offline</span>';
        }
    };

    window.addEventListener('online', updateStatus);
    window.addEventListener('offline', updateStatus);
    updateStatus();
}

function setupOfflineQueueUI() {
    const statusDiv = document.getElementById('connection-status');
    if (!statusDiv || !statusDiv.parentElement) return;
    if (!document.getElementById('offline-queue-btn')) {
        const button = document.createElement('button');
        button.id = 'offline-queue-btn';
        button.type = 'button';
        button.className = 'touch-target px-3 py-1 rounded-full text-xs font-bold border border-gray-200 text-gray-600 hover:bg-gray-50 transition-all';
        button.textContent = 'Pendências 0';
        button.addEventListener('click', () => openOfflineQueueModal());
        statusDiv.parentElement.insertBefore(button, statusDiv.nextSibling);
    }
    const refreshBadge = () => {
        const button = document.getElementById('offline-queue-btn');
        if (!button || !api.getOfflineQueueSummary) return;
        const summary = api.getOfflineQueueSummary();
        button.textContent = `Pendências ${summary.total}`;
        if (summary.total > 0) {
            button.className = 'touch-target px-3 py-1 rounded-full text-xs font-bold border border-amber-300 text-amber-700 bg-amber-50 hover:bg-amber-100 transition-all';
        } else {
            button.className = 'touch-target px-3 py-1 rounded-full text-xs font-bold border border-gray-200 text-gray-600 hover:bg-gray-50 transition-all';
        }
        const listContainer = document.getElementById('offline-queue-list');
        if (listContainer) {
            listContainer.innerHTML = buildOfflineQueueRows();
        }
        const summaryText = document.getElementById('offline-queue-summary');
        if (summaryText) {
            summaryText.textContent = buildOfflineQueueSummaryText(summary);
        }
    };
    window.addEventListener('offline-queue-changed', refreshBadge);
    refreshBadge();
}

function setupPendingQueueProtection() {
    window.addEventListener('beforeunload', (event) => {
        if (!api.getOfflineQueueSummary) return;
        const summary = api.getOfflineQueueSummary();
        if (summary.total > 0) {
            event.preventDefault();
            event.returnValue = 'Existem pendências offline aguardando sincronização.';
        }
    });
}

function buildOfflineQueueSummaryText(summary) {
    return `Total: ${summary.total} | Pendentes: ${summary.pending} | Falhas: ${summary.failed} | Sincronizando: ${summary.syncing}`;
}

function buildOfflineQueueRows() {
    if (!api.getOfflineQueueItems) return '';
    const queueItems = api.getOfflineQueueItems();
    if (!queueItems.length) {
        return '<div class="text-center text-gray-400 py-8">Nenhuma pendência offline.</div>';
    }
    return queueItems.map((item) => {
        const statusStyles = {
            pending: 'bg-amber-50 text-amber-700',
            failed: 'bg-red-50 text-red-700',
            syncing: 'bg-blue-50 text-blue-700'
        };
        const statusClass = statusStyles[item.status] || 'bg-gray-50 text-gray-700';
        const dateLabel = item.created_at ? new Date(item.created_at).toLocaleString('pt-BR') : '-';
        const lastError = item.last_error ? `<p class="text-xs text-red-500 mt-1 break-words">${item.last_error}</p>` : '';
        return `
            <div class="border border-gray-100 rounded-xl p-4">
                <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                        <p class="font-semibold text-gray-800 break-all">${item.method} ${item.endpoint}</p>
                        <p class="text-xs text-gray-400 mt-1">Criado em: ${dateLabel} | Tentativas: ${item.attempts || 0}</p>
                        ${lastError}
                    </div>
                    <span class="px-2 py-1 rounded-full text-xs font-bold ${statusClass}">${item.status || 'pending'}</span>
                </div>
            </div>
        `;
    }).join('');
}

function openOfflineQueueModal() {
    const summary = api.getOfflineQueueSummary ? api.getOfflineQueueSummary() : { total: 0, pending: 0, failed: 0, syncing: 0 };
    const content = `
        <h3 class="text-2xl font-bold mb-2 text-gray-800">Pendências Offline</h3>
        <p id="offline-queue-summary" class="text-sm text-gray-500 mb-6">${buildOfflineQueueSummaryText(summary)}</p>
        <div id="offline-queue-list" class="space-y-3 max-h-[50vh] overflow-y-auto pr-1">${buildOfflineQueueRows()}</div>
        <div class="flex justify-end gap-3 pt-6">
            <button type="button" onclick="closeModal()" class="px-6 py-3 rounded-xl text-gray-500 hover:bg-gray-100 font-bold">Fechar</button>
            <button type="button" id="sync-offline-now-btn" class="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold">Reenviar pendências agora</button>
        </div>
    `;
    openModal(content);
    document.getElementById('sync-offline-now-btn').addEventListener('click', async () => {
        if (!navigator.onLine) {
            showToast('Conecte-se à internet para reenviar as pendências.', 'warning');
            return;
        }
        await api.syncOfflineData();
        const refreshedSummary = api.getOfflineQueueSummary ? api.getOfflineQueueSummary() : summary;
        document.getElementById('offline-queue-list').innerHTML = buildOfflineQueueRows();
        document.getElementById('offline-queue-summary').textContent = buildOfflineQueueSummaryText(refreshedSummary);
    });
}

function setupNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = link.getAttribute('data-view');
            renderView(view);
            closeSidebarOnMobile();
        });
    });
}

function setupResponsiveMenu() {
    const menuBtn = document.getElementById('mobile-menu-btn');
    const closeBtn = document.getElementById('mobile-close-sidebar-btn');
    const overlay = document.getElementById('mobile-sidebar-overlay');
    const sidebar = document.getElementById('app-sidebar');
    if (!menuBtn || !closeBtn || !overlay || !sidebar) return;

    const openSidebar = () => {
        sidebar.classList.add('sidebar-mobile-open');
        overlay.classList.remove('hidden');
    };
    const closeSidebar = () => {
        sidebar.classList.remove('sidebar-mobile-open');
        overlay.classList.add('hidden');
    };
    menuBtn.addEventListener('click', openSidebar);
    closeBtn.addEventListener('click', closeSidebar);
    overlay.addEventListener('click', closeSidebar);
    window.addEventListener('resize', () => {
        if (window.innerWidth > 1024) {
            closeSidebar();
        }
    });
}

function closeSidebarOnMobile() {
    if (window.innerWidth > 1024) return;
    const sidebar = document.getElementById('app-sidebar');
    const overlay = document.getElementById('mobile-sidebar-overlay');
    if (sidebar && overlay) {
        sidebar.classList.remove('sidebar-mobile-open');
        overlay.classList.add('hidden');
    }
}

async function renderView(viewName) {
    const container = document.getElementById('view-container');
    const title = document.getElementById('current-view-title');
    
    // Update active state in navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('data-view') === viewName) {
            link.classList.add('sidebar-active', 'bg-pastel-blue', 'text-blue-600');
            link.classList.remove('text-gray-600');
        } else {
            link.classList.remove('sidebar-active', 'bg-pastel-blue', 'text-blue-600');
            link.classList.add('text-gray-600');
        }
    });

    container.innerHTML = '<div class="flex items-center justify-center h-full"><i class="fas fa-circle-notch fa-spin text-4xl text-blue-200"></i></div>';

    try {
        switch (viewName) {
            case 'dashboard':
                title.textContent = 'Dashboard';
                await renderDashboard(container);
                break;
            case 'products':
                title.textContent = 'Gestão de Produtos';
                await renderProducts(container);
                break;
            case 'clients':
                title.textContent = 'Gestão de Clientes';
                await renderClients(container);
                break;
            case 'sales':
                title.textContent = 'Vendas';
                await renderSales(container);
                break;
            case 'purchases':
                title.textContent = 'Compras';
                await renderPurchases(container);
                break;
            case 'finance':
                title.textContent = 'Financeiro';
                await renderFinance(container);
                break;
            case 'reports':
                title.textContent = 'Relatórios';
                await renderReports(container);
                break;
            default:
                container.innerHTML = '<h1>Em desenvolvimento</h1>';
        }
    } catch (error) {
        showToast('Erro ao carregar view: ' + error.message, 'error');
        container.innerHTML = `<div class="bg-red-50 p-8 rounded-2xl text-red-500 text-center">
            <i class="fas fa-exclamation-triangle text-4xl mb-4"></i>
            <p class="font-bold">Ops! Algo deu errado.</p>
            <p>${error.message}</p>
        </div>`;
    }
}

// VIEW RENDERING FUNCTIONS

async function renderDashboard(container) {
    const stats = await api.getDashboardStats();
    
    container.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 transition-all hover:shadow-md">
                <div class="flex items-center gap-4 mb-4">
                    <div class="bg-pastel-green w-12 h-12 rounded-xl flex items-center justify-center text-green-600">
                        <i class="fas fa-dollar-sign text-xl"></i>
                    </div>
                    <span class="text-sm font-medium text-gray-500 uppercase tracking-wider">Vendas Hoje</span>
                </div>
                <div class="text-2xl font-bold text-gray-900">R$ ${parseFloat(stats.vendas_dia).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
            </div>

            <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 transition-all hover:shadow-md">
                <div class="flex items-center gap-4 mb-4">
                    <div class="bg-pastel-blue w-12 h-12 rounded-xl flex items-center justify-center text-blue-600">
                        <i class="fas fa-calendar-check text-xl"></i>
                    </div>
                    <span class="text-sm font-medium text-gray-500 uppercase tracking-wider">Vendas Mês</span>
                </div>
                <div class="text-2xl font-bold text-gray-900">R$ ${parseFloat(stats.vendas_mes).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
            </div>

            <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 transition-all hover:shadow-md">
                <div class="flex items-center gap-4 mb-4">
                    <div class="bg-pastel-pink w-12 h-12 rounded-xl flex items-center justify-center text-pink-600">
                        <i class="fas fa-boxes-stacked text-xl"></i>
                    </div>
                    <span class="text-sm font-medium text-gray-500 uppercase tracking-wider">Estoque Baixo</span>
                </div>
                <div class="text-2xl font-bold text-gray-900">${stats.estoque_baixo_count} <span class="text-sm font-normal text-gray-400">itens</span></div>
            </div>

            <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 transition-all hover:shadow-md">
                <div class="flex items-center gap-4 mb-4">
                    <div class="bg-pastel-orange w-12 h-12 rounded-xl flex items-center justify-center text-orange-600">
                        <i class="fas fa-hand-holding-dollar text-xl"></i>
                    </div>
                    <span class="text-sm font-medium text-gray-500 uppercase tracking-wider">A Receber</span>
                </div>
                <div class="text-2xl font-bold text-gray-900">R$ ${parseFloat(stats.contas_receber_pendentes).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div class="bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
                <h3 class="text-lg font-bold mb-6 text-gray-800">Top 5 Produtos Vendidos</h3>
                <div class="space-y-6">
                    ${stats.top_produtos.length ? stats.top_produtos.map(p => `
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-4">
                                <div class="w-10 h-10 rounded-full bg-gray-50 flex items-center justify-center font-bold text-gray-400 text-sm">
                                    ${p.produto__descricao.substring(0, 2).toUpperCase()}
                                </div>
                                <span class="font-medium text-gray-700">${p.produto__descricao}</span>
                            </div>
                            <span class="bg-pastel-blue text-blue-600 px-3 py-1 rounded-full text-sm font-bold">${p.total_vendido} vendidos</span>
                        </div>
                    `).join('') : '<p class="text-gray-400 text-center py-4">Nenhuma venda registrada.</p>'}
                </div>
            </div>

            <div class="bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
                <h3 class="text-lg font-bold mb-6 text-gray-800">Resumo Financeiro</h3>
                <div class="space-y-4">
                    <div class="p-4 bg-pastel-green rounded-2xl flex items-center justify-between">
                        <div class="flex items-center gap-4">
                            <div class="bg-white/50 p-2 rounded-lg"><i class="fas fa-arrow-trend-up text-green-600"></i></div>
                            <span class="font-medium">Vendas Realizadas</span>
                        </div>
                        <span class="font-bold">R$ ${parseFloat(stats.vendas_mes).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div id="dashboard-card-payable" class="p-4 bg-pastel-pink rounded-2xl flex items-center justify-between cursor-pointer hover:shadow-md transition-all">
                        <div class="flex items-center gap-4">
                            <div class="bg-white/50 p-2 rounded-lg"><i class="fas fa-arrow-trend-down text-pink-600"></i></div>
                            <span class="font-medium">Contas a Pagar</span>
                        </div>
                        <span class="font-bold">R$ ${parseFloat(stats.contas_pagar_pendentes).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div id="dashboard-card-receivable" class="p-4 bg-pastel-blue rounded-2xl flex items-center justify-between cursor-pointer hover:shadow-md transition-all">
                        <div class="flex items-center gap-4">
                            <div class="bg-white/50 p-2 rounded-lg"><i class="fas fa-wallet text-blue-600"></i></div>
                            <span class="font-medium">Contas a Receber</span>
                        </div>
                        <span class="font-bold">R$ ${parseFloat(stats.contas_receber_pendentes).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    const payableCard = document.getElementById('dashboard-card-payable');
    const receivableCard = document.getElementById('dashboard-card-receivable');
    if (payableCard) {
        payableCard.addEventListener('click', () => {
            window.financeFocus = 'payable';
            renderView('finance');
        });
    }
    if (receivableCard) {
        receivableCard.addEventListener('click', () => {
            window.financeFocus = 'receivable';
            renderView('finance');
        });
    }
}

async function renderProducts(container) {
    const products = await api.getProducts();
    
    container.innerHTML = `
        <div class="flex justify-between items-center mb-8 gap-4 flex-wrap">
            <div class="relative w-96">
                <i class="fas fa-search absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                <input type="text" id="product-search" placeholder="Buscar produtos..." class="w-full pl-12 pr-4 py-3 bg-white border border-gray-100 rounded-xl focus:ring-2 focus:ring-blue-100 outline-none transition-all shadow-sm">
            </div>
            <div class="flex items-center gap-3">
                <button id="quick-category-page-btn" class="bg-blue-100 hover:bg-blue-200 text-blue-700 px-4 py-3 rounded-xl font-bold flex items-center gap-2 transition-all">
                    <i class="fas fa-tags"></i>
                    Nova Categoria
                </button>
                <button id="add-product-btn" class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-bold flex items-center gap-3 transition-all transform active:scale-95 shadow-lg shadow-blue-100">
                    <i class="fas fa-plus"></i>
                    Novo Produto
                </button>
            </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto">
            <table class="w-full text-left">
                <thead class="bg-gray-50 border-b border-gray-100">
                    <tr>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Produto</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Categoria</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Estoque</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Preço Venda</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider text-right">Ações</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                    ${(products || []).map(p => {
                        const currentStock = parseFloat(p.estoque_atual || 0);
                        const minStock = parseFloat(p.estoque_minimo || 0);
                        const isLowStock = Number.isFinite(currentStock) && Number.isFinite(minStock) ? currentStock <= minStock : false;
                        return `
                        <tr class="hover:bg-gray-50/50 transition-all group">
                            <td class="px-8 py-5">
                                <div class="flex flex-col">
                                    <span class="font-bold text-gray-800">${p.descricao}</span>
                                    <span class="text-xs text-gray-400 font-mono">${p.sku}</span>
                                </div>
                            </td>
                            <td class="px-8 py-5">
                                <span class="bg-pastel-blue text-blue-600 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide">${p.categoria_nome || 'Sem Categoria'}</span>
                            </td>
                            <td class="px-8 py-5">
                                <div class="flex items-center gap-2">
                                    <span class="font-bold ${isLowStock ? 'text-red-500' : 'text-gray-700'}">${p.estoque_atual}</span>
                                    <span class="text-xs text-gray-400 uppercase">${p.unidade_sigla || ''}</span>
                                </div>
                            </td>
                            <td class="px-8 py-5">
                                <span class="font-bold text-gray-900">R$ ${parseFloat(p.preco_venda).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                            </td>
                            <td class="px-8 py-5 text-right">
                                <div class="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button onclick="editProduct(${p.id})" class="p-2 text-blue-500 hover:bg-blue-50 rounded-lg transition-all" title="Editar">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button onclick="deleteProduct(${p.id})" class="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-all" title="Excluir">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;

    document.getElementById('add-product-btn').addEventListener('click', () => openProductForm());
    document.getElementById('quick-category-page-btn').addEventListener('click', () => {
        openQuickCategoryModal(() => {
            renderView('products');
        });
    });
    
    // Simple search filter
    document.getElementById('product-search').addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const rows = document.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const text = row.innerText.toLowerCase();
            row.style.display = text.includes(query) ? '' : 'none';
        });
    });
}

async function renderClients(container) {
    const clients = await api.getClients();

    container.innerHTML = `
        <div class="flex justify-between items-center mb-8">
            <h3 class="text-2xl font-bold text-gray-800">Clientes Cadastrados</h3>
            <button id="add-client-btn" class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-bold flex items-center gap-3">
                <i class="fas fa-plus"></i>
                Novo Cliente
            </button>
        </div>
        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto">
            <table class="w-full text-left">
                <thead class="bg-gray-50 border-b border-gray-100">
                    <tr>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Nome</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">CPF/CNPJ</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Contato</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider text-right">Ações</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                    ${(clients || []).map(c => `
                        <tr class="hover:bg-gray-50/50 transition-all group">
                            <td class="px-8 py-5 font-bold text-gray-800">${c.nome}</td>
                            <td class="px-8 py-5 text-gray-500">${c.cpf_cnpj}</td>
                            <td class="px-8 py-5 text-gray-500">${formatContact(c.email, c.telefone)}</td>
                            <td class="px-8 py-5 text-right">
                                <div class="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button onclick="editClient(${c.id})" class="p-2 text-blue-500 hover:bg-blue-50 rounded-lg" title="Editar"><i class="fas fa-edit"></i></button>
                                    <button onclick="deleteClient(${c.id})" class="p-2 text-red-500 hover:bg-red-50 rounded-lg" title="Excluir"><i class="fas fa-trash"></i></button>
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;

    document.getElementById('add-client-btn').addEventListener('click', () => openClientForm());
}

// Helper UI functions
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const content = document.getElementById('toast-content');
    const icon = document.getElementById('toast-icon');
    const msg = document.getElementById('toast-message');

    msg.textContent = message;
    
    if (type === 'success') {
        icon.className = 'w-8 h-8 rounded-full flex items-center justify-center text-white bg-green-500';
        icon.innerHTML = '<i class="fas fa-check"></i>';
    } else if (type === 'info') {
        icon.className = 'w-8 h-8 rounded-full flex items-center justify-center text-white bg-blue-500';
        icon.innerHTML = '<i class="fas fa-info"></i>';
    } else if (type === 'warning') {
        icon.className = 'w-8 h-8 rounded-full flex items-center justify-center text-white bg-amber-500';
        icon.innerHTML = '<i class="fas fa-triangle-exclamation"></i>';
    } else {
        icon.className = 'w-8 h-8 rounded-full flex items-center justify-center text-white bg-red-500';
        icon.innerHTML = '<i class="fas fa-exclamation"></i>';
    }

    toast.classList.remove('translate-y-20', 'opacity-0');
    
    setTimeout(() => {
        toast.classList.add('translate-y-20', 'opacity-0');
    }, 3000);
}

function resolveMutationResult(result, successMessage, queuedMessage) {
    if (result && result.offline) {
        showToast(queuedMessage || 'Operação salva offline e pendente de sincronização.', 'warning');
        return true;
    }
    showToast(successMessage, 'success');
    return false;
}

function openModal(content) {
    const modal = document.getElementById('modal-container');
    const body = document.getElementById('modal-body');
    body.innerHTML = content;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeModal() {
    const modal = document.getElementById('modal-container');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

function openConfirmModal(message, onConfirm) {
    const overlay = document.createElement('div');
    overlay.id = 'confirm-overlay';
    overlay.className = 'fixed inset-0 bg-black/50 flex items-center justify-center z-[120] p-4';
    overlay.innerHTML = `
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8 text-center">
            <div class="bg-red-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6 text-red-500">
                <i class="fas fa-exclamation-triangle text-2xl"></i>
            </div>
            <h3 class="text-xl font-bold mb-4 text-gray-800">Confirmar Exclusão</h3>
            <p class="text-gray-500 mb-8">${message}</p>
            <div class="flex justify-center gap-4">
                <button type="button" id="confirm-cancel-btn" class="px-6 py-3 rounded-xl text-gray-500 hover:bg-gray-100 font-bold transition-all">Cancelar</button>
                <button type="button" id="confirm-action-btn" class="bg-red-500 hover:bg-red-600 text-white px-8 py-3 rounded-xl font-bold shadow-lg transition-all transform active:scale-95">Confirmar</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    document.getElementById('confirm-cancel-btn').onclick = () => overlay.remove();
    document.getElementById('confirm-action-btn').onclick = () => {
        onConfirm();
        overlay.remove();
    };
}

function formatDocumentDigits(value) {
    return String(value || '').replace(/\D/g, '');
}

function formatContact(email, phone) {
    const normalizedEmail = (email && String(email).toLowerCase() !== 'null') ? String(email).trim() : '';
    const normalizedPhone = (phone && String(phone).toLowerCase() !== 'null') ? String(phone).trim() : '';
    if (normalizedEmail && normalizedPhone) {
        return `${normalizedEmail} / ${normalizedPhone}`;
    }
    if (normalizedEmail) {
        return normalizedEmail;
    }
    if (normalizedPhone) {
        return normalizedPhone;
    }
    return '-';
}

async function openQuickCategoryModal(onCreated) {
    const content = `
        <h3 class="text-2xl font-bold mb-6 text-gray-800">Nova Categoria</h3>
        <form id="quick-category-form" class="space-y-4">
            <div>
                <label class="block text-sm font-semibold text-gray-700 mb-2">Nome da Categoria</label>
                <input type="text" name="nome" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50" required>
            </div>
            <div class="flex justify-end gap-3 pt-2">
                <button type="button" onclick="closeModal()" class="px-6 py-3 rounded-xl text-gray-500 hover:bg-gray-100 font-bold">Cancelar</button>
                <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold">Salvar</button>
            </div>
        </form>
    `;
    openModal(content);
    document.getElementById('quick-category-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        try {
            const result = await api.createCategory(data);
            const queued = resolveMutationResult(result, 'Categoria criada com sucesso!', 'Categoria salva offline. Será sincronizada quando houver internet.');
            if (!queued && onCreated) {
                onCreated(result);
            }
            closeModal();
        } catch (error) {
            showToast(error.message, 'error');
        }
    });
}

async function openQuickSupplierModal(onCreated) {
    const content = `
        <h3 class="text-2xl font-bold mb-6 text-gray-800">Adicionar Fornecedor</h3>
        <form id="quick-supplier-form" class="space-y-4">
            <div>
                <label class="block text-sm font-semibold text-gray-700 mb-2">Nome/Razão Social</label>
                <input type="text" name="razao_social" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50" required>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-2">CNPJ/CPF</label>
                    <input type="text" name="cnpj" id="quick-supplier-document" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50" required>
                </div>
                <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-2">Telefone</label>
                    <input type="text" name="telefone" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50" required>
                </div>
            </div>
            <div>
                <label class="block text-sm font-semibold text-gray-700 mb-2">E-mail (opcional)</label>
                <input type="email" name="email" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">
            </div>
            <div class="flex justify-end gap-3 pt-2">
                <button type="button" onclick="closeModal()" class="px-6 py-3 rounded-xl text-gray-500 hover:bg-gray-100 font-bold">Cancelar</button>
                <button type="submit" class="bg-orange-500 hover:bg-orange-600 text-white px-8 py-3 rounded-xl font-bold">Salvar</button>
            </div>
        </form>
    `;
    openModal(content);
    const documentInput = document.getElementById('quick-supplier-document');
    documentInput.addEventListener('input', () => {
        documentInput.value = formatDocumentDigits(documentInput.value);
    });
    document.getElementById('quick-supplier-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        data.cnpj = formatDocumentDigits(data.cnpj);
        try {
            const result = await api.createSupplier(data);
            const queued = resolveMutationResult(result, 'Fornecedor criado com sucesso!', 'Fornecedor salvo offline. Será sincronizado quando houver internet.');
            if (!queued && onCreated) {
                onCreated(result);
            }
            closeModal();
        } catch (error) {
            showToast(error.message, 'error');
        }
    });
}

// Global functions for inline event handlers
window.editProduct = async (id) => {
    try {
        const product = await api.getProduct(id);
        openProductForm(product);
    } catch (error) {
        showToast(error.message, 'error');
    }
};

window.deleteProduct = async (id) => {
    openConfirmModal('Excluir este produto pode desativar o cadastro quando existir histórico de compras, vendas ou estoque. Deseja continuar?', async () => {
        try {
            const result = await api.deleteProduct(id);
            const queued = resolveMutationResult(result, 'Produto excluído com sucesso!', 'Exclusão salva offline. Será aplicada quando a internet voltar.');
            if (!queued) {
                renderView('products');
            }
        } catch (error) {
            showToast(error.message, 'error');
        }
    });
};

window.editClient = async (id) => {
    try {
        const client = await api.getClient(id);
        openClientForm(client);
    } catch (error) {
        showToast(error.message, 'error');
    }
};

window.deleteClient = async (id) => {
    openConfirmModal('Excluir este cliente pode desativar o cadastro para preservar histórico de vendas e financeiro. Deseja continuar?', async () => {
        try {
            const result = await api.deleteClient(id);
            const queued = resolveMutationResult(result, 'Cliente excluído com sucesso!', 'Exclusão salva offline. Será aplicada quando a internet voltar.');
            if (!queued) {
                renderView('clients');
            }
        } catch (error) {
            showToast(error.message, 'error');
        }
    });
};

async function openClientForm(client = null) {
    const isEdit = !!client;
    const title = isEdit ? 'Editar Cliente' : 'Novo Cliente';

    const content = `
        <h3 class="text-2xl font-bold mb-8 text-gray-800">${title}</h3>
        <form id="client-form" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-2">Nome Completo</label>
                    <input type="text" name="nome" value="${client?.nome || ''}" class="w-full px-4 py-3 rounded-xl border bg-gray-50" required>
                </div>
                <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-2">CPF/CNPJ</label>
                    <input type="text" name="cpf_cnpj" value="${client?.cpf_cnpj || ''}" class="w-full px-4 py-3 rounded-xl border bg-gray-50">
                </div>
                <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-2">Telefone</label>
                    <input type="text" name="telefone" value="${client?.telefone || ''}" class="w-full px-4 py-3 rounded-xl border bg-gray-50">
                </div>
                <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-2">E-mail</label>
                    <input type="email" name="email" value="${client?.email || ''}" class="w-full px-4 py-3 rounded-xl border bg-gray-50">
                </div>
                <div class="col-span-2">
                    <label class="block text-sm font-semibold text-gray-700 mb-2">Endereço</label>
                    <textarea name="endereco_entrega" class="w-full px-4 py-3 rounded-xl border bg-gray-50" rows="3">${client?.endereco_entrega || ''}</textarea>
                </div>
            </div>
            <div class="flex justify-end gap-4 mt-8 pt-6 border-t">
                <button type="button" onclick="closeModal()" class="px-6 py-3 rounded-xl text-gray-500 hover:bg-gray-100 font-bold">Cancelar</button>
                <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold">${isEdit ? 'Salvar Alterações' : 'Cadastrar Cliente'}</button>
            </div>
        </form>
    `;

    openModal(content);

    document.getElementById('client-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());

        try {
            if (isEdit) {
                const result = await api.updateClient(client.id, data);
                const queued = resolveMutationResult(result, 'Cliente atualizado com sucesso!', 'Atualização salva offline. Será enviada automaticamente quando a internet voltar.');
                closeModal();
                if (!queued) {
                    renderView('clients');
                }
            } else {
                const result = await api.createClient(data);
                const queued = resolveMutationResult(result, 'Cliente cadastrado com sucesso!', 'Cadastro salvo offline. Será enviado automaticamente quando a internet voltar.');
                closeModal();
                if (!queued) {
                    renderView('clients');
                }
            }
        } catch (error) {
            showToast(error.message, 'error');
        }
    });
}

async function openProductForm(product = null) {
    try {
        const categoriesData = await api.getCategories();
        
        const categories = Array.isArray(categoriesData) ? categoriesData : (categoriesData.results || []);
        
        const isEdit = !!product;
        const title = isEdit ? 'Editar Produto' : 'Novo Produto';
        
        const content = `
            <h3 class="text-2xl font-bold mb-8 text-gray-800">${title}</h3>
            <form id="product-form" class="space-y-6">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label class="block text-sm font-semibold text-gray-700 mb-2">Descrição do Produto</label>
                        <input type="text" name="descricao" value="${product?.descricao || ''}" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-100 outline-none transition-all" required>
                    </div>
                    <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-2">Nome</label>
                    <input type="text" name="sku" value="${product?.sku || ''}" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-100 outline-none transition-all" required>
                </div>
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <label class="block text-sm font-semibold text-gray-700">Categoria</label>
                        <button type="button" id="quick-add-category-btn" class="text-xs bg-blue-100 text-blue-600 px-3 py-1 rounded-lg font-bold">Nova Categoria</button>
                    </div>
                    <select name="categoria" id="product-category-select" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-100 outline-none transition-all" required>
                        ${categories.map(c => `<option value="${c.id}" ${product?.categoria === c.id ? 'selected' : ''}>${c.nome}</option>`).join('')}
                    </select>
                </div>
                    <div>
                        <label class="block text-sm font-semibold text-gray-700 mb-2">Preço de Custo (R$)</label>
                        <input type="number" step="0.01" name="preco_custo" value="${product?.preco_custo || ''}" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-100 outline-none transition-all" required>
                    </div>
                    <div>
                        <label class="block text-sm font-semibold text-gray-700 mb-2">Preço de Venda (R$)</label>
                        <input type="number" step="0.01" name="preco_venda" value="${product?.preco_venda || ''}" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-100 outline-none transition-all" required>
                    </div>
                    <div class="col-span-1">
                    <label class="block text-sm font-semibold text-gray-700 mb-2">Estoque Mínimo</label>
                    <input type="number" name="estoque_minimo" value="${product?.estoque_minimo || '0'}" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-100 outline-none transition-all">
                </div>
                ${!isEdit ? `
                <div class="col-span-1">
                    <label class="block text-sm font-semibold text-gray-700 mb-2">Quantidade Inicial</label>
                    <input type="number" name="estoque_atual" value="0" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-100 outline-none transition-all">
                </div>
                ` : ''}
                <div class="col-span-1">
                      <label class="block text-sm font-semibold text-gray-700 mb-2">Código de Barras</label>
                      <div class="flex gap-2">
                          <input type="text" id="barcode-input" name="codigo_barras" value="${product?.codigo_barras || ''}" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-100 outline-none transition-all" placeholder="0 000000 000000">
                          <button type="button" id="start-scanner-btn" class="bg-blue-100 text-blue-600 px-4 py-3 rounded-xl hover:bg-blue-200 transition-all">
                              <i class="fas fa-camera"></i>
                          </button>
                      </div>
                      <div id="reader" class="mt-4 hidden w-full overflow-hidden rounded-xl border border-gray-200"></div>
                 </div>
                </div>
                
                <div class="flex justify-end gap-4 mt-8 pt-6 border-t border-gray-50">
                    <button type="button" onclick="closeModal()" class="px-6 py-3 rounded-xl text-gray-500 hover:bg-gray-100 font-bold transition-all">Cancelar</button>
                    <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold shadow-lg shadow-blue-100 transition-all transform active:scale-95">
                        ${isEdit ? 'Salvar Alterações' : 'Cadastrar Produto'}
                    </button>
                </div>
            </form>
        `;
        
        openModal(content);
        const categorySelect = document.getElementById('product-category-select');
        document.getElementById('quick-add-category-btn').addEventListener('click', () => {
            openQuickCategoryModal(async (newCategory) => {
                const categoriesRefreshed = await api.getCategories();
                const list = Array.isArray(categoriesRefreshed) ? categoriesRefreshed : (categoriesRefreshed.results || []);
                categorySelect.innerHTML = list.map(c => `<option value="${c.id}" ${newCategory?.id === c.id ? 'selected' : ''}>${c.nome}</option>`).join('');
                if (newCategory?.id) {
                    categorySelect.value = String(newCategory.id);
                }
                showToast('Categoria disponível para seleção.', 'success');
            });
        });
        
        const barcodeInput = document.getElementById('barcode-input');
        const startScannerBtn = document.getElementById('start-scanner-btn');
        const readerDiv = document.getElementById('reader');
        let html5QrCode;

        // Barcode Mask (EAN-13 style: 0 000000 000000)
        barcodeInput.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 13) value = value.slice(0, 13);
            
            let formatted = '';
            if (value.length > 0) formatted += value[0];
            if (value.length > 1) formatted += ' ' + value.slice(1, 7);
            if (value.length > 7) formatted += ' ' + value.slice(7, 13);
            
            e.target.value = formatted.trim();
        });

        // Camera Scanner Logic
        startScannerBtn.addEventListener('click', async () => {
            if (html5QrCode) {
                await html5QrCode.stop();
                html5QrCode = null;
                readerDiv.classList.add('hidden');
                startScannerBtn.innerHTML = '<i class="fas fa-camera"></i>';
                return;
            }

            readerDiv.classList.remove('hidden');
            startScannerBtn.innerHTML = '<i class="fas fa-times"></i>';
            html5QrCode = new Html5Qrcode("reader");
            
            try {
                await html5QrCode.start(
                    { facingMode: "environment" },
                    { fps: 10, qrbox: { width: 250, height: 150 } },
                    (decodedText) => {
                        barcodeInput.value = decodedText;
                        barcodeInput.dispatchEvent(new Event('input'));
                        showToast('Código capturado!', 'success');
                        html5QrCode.stop();
                        html5QrCode = null;
                        readerDiv.classList.add('hidden');
                        startScannerBtn.innerHTML = '<i class="fas fa-camera"></i>';
                    }
                );
            } catch (err) {
                showToast('Erro ao acessar câmera: ' + err, 'error');
                readerDiv.classList.add('hidden');
                startScannerBtn.innerHTML = '<i class="fas fa-camera"></i>';
            }
        });

        // Ensure scanner stops when modal closes
        const originalCloseModal = window.closeModal;
        window.closeModal = async () => {
            if (html5QrCode) {
                await html5QrCode.stop();
            }
            originalCloseModal();
            window.closeModal = originalCloseModal;
        };
        
        document.getElementById('product-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());
            const barcodeDigits = formatDocumentDigits(data.codigo_barras || '');
            data.codigo_barras = barcodeDigits || null;
            
            try {
                if (isEdit) {
                    const result = await api.updateProduct(product.id, data);
                    const queued = resolveMutationResult(result, 'Produto atualizado com sucesso!', 'Atualização salva offline. Será enviada automaticamente quando a internet voltar.');
                    closeModal();
                    if (!queued) {
                        renderView('products');
                    }
                } else {
                    const result = await api.createProduct(data);
                    const queued = resolveMutationResult(result, 'Produto cadastrado com sucesso!', 'Cadastro salvo offline. Será enviado automaticamente quando a internet voltar.');
                    closeModal();
                    if (!queued) {
                        renderView('products');
                    }
                }
            } catch (error) {
                showToast(error.message, 'error');
            }
        });
    } catch (error) {
        showToast('Erro ao carregar formulário: ' + error.message, 'error');
    }
}

// Sales Module
async function renderSales(container) {
    const sales = await api.getSales();
    
    container.innerHTML = `
        <div class="flex justify-between items-center mb-8">
            <h3 class="text-2xl font-bold text-gray-800">Histórico de Vendas</h3>
            <button id="new-sale-btn" class="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-xl font-bold flex items-center gap-3 transition-all transform active:scale-95 shadow-lg shadow-green-100">
                <i class="fas fa-cart-plus"></i>
                Nova Venda
            </button>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto">
            <table class="w-full text-left">
                <thead class="bg-gray-50 border-b border-gray-100">
                    <tr>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">ID</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Cliente</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Data</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Total</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider text-right">Ações</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                    ${(sales || []).length ? sales.map(s => `
                        <tr class="hover:bg-gray-50/50 transition-all group">
                            <td class="px-8 py-5 text-gray-400 font-mono text-xs">#${s.id}</td>
                            <td class="px-8 py-5">
                                <span class="font-bold text-gray-800">${s.cliente_nome || 'Cliente #' + s.cliente}</span>
                            </td>
                            <td class="px-8 py-5 text-gray-500">
                                ${new Date(s.data_venda).toLocaleDateString('pt-BR')}
                            </td>
                            <td class="px-8 py-5">
                                <span class="font-bold text-green-600">R$ ${parseFloat(s.valor_total).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                            </td>
                            <td class="px-8 py-5 text-right">
                                <button class="p-2 text-gray-400 hover:text-blue-500 transition-all">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('') : '<tr><td colspan="5" class="p-8 text-center text-gray-400">Nenhuma venda registrada.</td></tr>'}
                </tbody>
            </table>
        </div>
    `;

    document.getElementById('new-sale-btn').addEventListener('click', () => openSaleForm());
}

async function openSaleForm() {
    try {
        const clientsData = await api.getClients();
        const productsData = await api.getProducts();
        const clients = Array.isArray(clientsData) ? clientsData : (clientsData.results || []);
        const products = Array.isArray(productsData) ? productsData : (productsData.results || []);

        let itemsHtml = '<div id="sale-items-container" class="space-y-4"></div>';

        const content = `
            <h3 class="text-2xl font-bold mb-8 text-gray-800">Registrar Nova Venda</h3>
            <form id="sale-form" class="space-y-6">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label class="block text-sm font-semibold text-gray-700 mb-2">Cliente</label>
                        <select name="cliente" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50" required>
                            ${clients.map(c => `<option value="${c.id}">${c.nome}</option>`).join('')}
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-semibold text-gray-700 mb-2">Status do Pagamento</label>
                        <select name="status_pagamento" id="sale-status-payment" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50" required>
                            <option value="pago">Pago</option>
                            <option value="pendente">Pendente</option>
                            <option value="atrasado">Não Pago</option>
                        </select>
                    </div>
                    <div id="due-date-container" class="hidden">
                        <label class="block text-sm font-semibold text-gray-700 mb-2">Data de Vencimento</label>
                        <input type="date" name="data_vencimento" id="sale-due-date" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">
                    </div>
                </div>
                <div class="pt-6 border-t border-gray-100">
                    <div class="flex justify-between items-center mb-4">
                        <h4 class="text-lg font-bold">Itens da Venda</h4>
                        <button type="button" id="add-sale-item" class="text-sm bg-blue-100 text-blue-600 px-4 py-2 rounded-lg font-bold">Adicionar Item</button>
                    </div>
                    ${itemsHtml}
                </div>
                <div class="flex justify-end gap-4 mt-8 pt-6 border-t border-gray-100">
                    <button type="button" onclick="closeModal()" class="px-6 py-3 rounded-xl text-gray-500 hover:bg-gray-100 font-bold">Cancelar</button>
                    <button type="submit" class="bg-green-600 hover:bg-green-700 text-white px-8 py-3 rounded-xl font-bold">Registrar Venda</button>
                </div>
            </form>
        `;

        openModal(content);

        const statusPayment = document.getElementById('sale-status-payment');
        const dueDateContainer = document.getElementById('due-date-container');
        const dueDateInput = document.getElementById('sale-due-date');

        statusPayment.addEventListener('change', () => {
            if (statusPayment.value !== 'pago') {
                dueDateContainer.classList.remove('hidden');
                dueDateInput.required = true;
            } else {
                dueDateContainer.classList.add('hidden');
                dueDateInput.required = false;
                dueDateInput.value = '';
            }
        });

        const addItemButton = document.getElementById('add-sale-item');
        const itemsContainer = document.getElementById('sale-items-container');

        let debounceTimer;
        addItemButton.addEventListener('click', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const itemIndex = Date.now();
                const newItemHtml = `
                    <div class="grid grid-cols-12 gap-4 p-4 bg-gray-50 rounded-lg" id="sale-item-${itemIndex}" data-item-key="${itemIndex}">
                        <div class="col-span-7">
                            <select name="items[${itemIndex}][produto]" class="w-full p-2 border rounded" required>
                                ${products.map(p => `<option value="${p.id}" data-price="${p.preco_venda}">${p.descricao}</option>`).join('')}
                            </select>
                        </div>
                        <div class="col-span-3">
                            <input type="number" name="items[${itemIndex}][quantidade]" placeholder="Qtd" class="w-full p-2 border rounded" required>
                        </div>
                        <div class="col-span-2 flex items-center justify-end">
                            <button type="button" onclick="removeSaleItem(${itemIndex})" class="text-red-500 hover:text-red-700"><i class="fas fa-trash"></i></button>
                        </div>
                    </div>
                `;
                itemsContainer.insertAdjacentHTML('beforeend', newItemHtml);
            }, 1000);
        });

        window.removeSaleItem = (index) => {
            openConfirmModal('Tem certeza que deseja remover este item da venda?', () => {
                document.getElementById(`sale-item-${index}`).remove();
            });
        };

        document.getElementById('sale-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const saleData = {
                cliente: formData.get('cliente'),
                status_pagamento: formData.get('status_pagamento'),
                data_vencimento: formData.get('data_vencimento') || null,
                itens: []
            };

            const items = [];
            const rows = itemsContainer.querySelectorAll('[data-item-key]');
            rows.forEach((row) => {
                const key = row.getAttribute('data-item-key');
                const produtoSelect = row.querySelector(`[name="items[${key}][produto]"]`);
                const quantidadeInput = row.querySelector(`[name="items[${key}][quantidade]"]`);
                const produto = produtoSelect ? produtoSelect.value : null;
                const quantidade = quantidadeInput ? quantidadeInput.value : null;
                const preco_unitario = produtoSelect?.selectedOptions?.[0]?.getAttribute('data-price');
                if (produto && quantidade) {
                    items.push({ produto, quantidade, preco_unitario });
                }
            });
            saleData.itens = items;

            try {
                if (saleData.itens.length === 0) {
                    showToast('Adicione pelo menos um item para registrar a venda.', 'error');
                    return;
                }
                const result = await api.createSale(saleData);
                const queued = resolveMutationResult(result, 'Venda registrada com sucesso!', 'Venda salva offline. Será sincronizada automaticamente quando houver internet.');
                closeModal();
                if (!queued) {
                    renderView('sales');
                }
            } catch (error) {
                showToast('Erro ao registrar venda: ' + error.message, 'error');
            }
        });

    } catch (error) {
        showToast('Erro ao abrir formulário de venda: ' + error.message, 'error');
    }
}

// Purchases Module
async function renderPurchases(container) {
    const purchases = await api.getPurchases();
    
    container.innerHTML = `
        <div class="flex justify-between items-center mb-8 gap-4 flex-wrap">
            <h3 class="text-2xl font-bold text-gray-800">Entrada de Mercadorias</h3>
            <div class="flex items-center gap-3">
                <button id="quick-supplier-page-btn" class="bg-orange-100 hover:bg-orange-200 text-orange-700 px-4 py-3 rounded-xl font-bold flex items-center gap-2 transition-all">
                    <i class="fas fa-building"></i>
                    Adicionar Fornecedor
                </button>
                <button id="new-purchase-btn" class="bg-orange-500 hover:bg-orange-600 text-white px-6 py-3 rounded-xl font-bold flex items-center gap-3 transition-all transform active:scale-95 shadow-lg shadow-orange-100">
                    <i class="fas fa-truck-loading"></i>
                    Registrar Compra
                </button>
            </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto">
            <table class="w-full min-w-[760px] text-left">
                <thead class="bg-gray-50 border-b border-gray-100">
                    <tr>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Nota Fiscal</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Fornecedor</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Data</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Total</th>
                        <th class="px-8 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider text-right">Ações</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                    ${(purchases || []).length ? purchases.map(p => `
                        <tr class="hover:bg-gray-50/50 transition-all group">
                            <td class="px-8 py-5 font-mono text-xs">${p.numero_nota_fiscal || '-'}</td>
                            <td class="px-8 py-5">
                                <span class="font-bold text-gray-800">${p.fornecedor_nome || 'Fornecedor #' + p.fornecedor}</span>
                            </td>
                            <td class="px-8 py-5 text-gray-500">
                                ${new Date(p.data_recebimento).toLocaleDateString('pt-BR')}
                            </td>
                            <td class="px-8 py-5">
                                <span class="font-bold text-orange-600">R$ ${parseFloat(p.valor_total).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                            </td>
                            <td class="px-8 py-5 text-right">
                                <button class="p-2 text-gray-400 hover:text-blue-500 transition-all">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('') : '<tr><td colspan="5" class="p-8 text-center text-gray-400">Nenhuma compra registrada.</td></tr>'}
                </tbody>
            </table>
        </div>
    `;

    document.getElementById('new-purchase-btn').addEventListener('click', () => openPurchaseForm());
    document.getElementById('quick-supplier-page-btn').addEventListener('click', () => {
        openQuickSupplierModal(() => {
            renderView('purchases');
        });
    });
}

async function openPurchaseForm() {
    try {
        const suppliersData = await api.getSuppliers();
        const productsData = await api.getProducts();
        const suppliers = Array.isArray(suppliersData) ? suppliersData : (suppliersData.results || []);
        const products = Array.isArray(productsData) ? productsData : (productsData.results || []);

        let itemsHtml = '<div id="purchase-items-container" class="space-y-4"></div>';

        const content = `
            <h3 class="text-2xl font-bold mb-8 text-gray-800">Registrar Nova Compra</h3>
            <form id="purchase-form" class="space-y-6">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <div class="flex items-center justify-between mb-2">
                            <label class="block text-sm font-semibold text-gray-700">Fornecedor</label>
                            <button type="button" id="quick-add-supplier-btn" class="text-xs bg-orange-100 text-orange-600 px-3 py-1 rounded-lg font-bold">Adicionar Fornecedor</button>
                        </div>
                        <select name="fornecedor" id="purchase-supplier-select" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50" required>
                            ${suppliers.map(s => `<option value="${s.id}">${s.razao_social}</option>`).join('')}
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-semibold text-gray-700 mb-2">Número da Nota Fiscal (opcional)</label>
                        <input type="text" name="numero_nota_fiscal" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">
                    </div>
                    <div>
                        <label class="block text-sm font-semibold text-gray-700 mb-2">Data de Emissão</label>
                        <input type="date" name="data_emissao" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50" required>
                    </div>
                    <div>
                        <label class="block text-sm font-semibold text-gray-700 mb-2">Data de Vencimento</label>
                        <input type="date" name="data_vencimento" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50" required>
                    </div>
                    <div>
                        <label class="block text-sm font-semibold text-gray-700 mb-2">Status do Pagamento</label>
                        <select name="status_pagamento" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50" required>
                            <option value="pago">Pago</option>
                            <option value="pendente">Pendente</option>
                            <option value="atrasado">Não Pago</option>
                        </select>
                    </div>
                </div>
                <div class="pt-6 border-t border-gray-100">
                    <div class="flex justify-between items-center mb-4">
                        <h4 class="text-lg font-bold">Itens da Compra</h4>
                        <button type="button" id="add-purchase-item" class="text-sm bg-blue-100 text-blue-600 px-4 py-2 rounded-lg font-bold">Adicionar Item</button>
                    </div>
                    ${itemsHtml}
                </div>
                <div class="flex justify-end gap-4 mt-8 pt-6 border-t border-gray-100">
                    <button type="button" onclick="closeModal()" class="px-6 py-3 rounded-xl text-gray-500 hover:bg-gray-100 font-bold">Cancelar</button>
                    <button type="submit" class="bg-orange-500 hover:bg-orange-600 text-white px-8 py-3 rounded-xl font-bold">Registrar Compra</button>
                </div>
            </form>
        `;

        openModal(content);
        const supplierSelect = document.getElementById('purchase-supplier-select');
        document.getElementById('quick-add-supplier-btn').addEventListener('click', () => {
            openQuickSupplierModal(async (newSupplier) => {
                const suppliersRefreshed = await api.getSuppliers();
                const list = Array.isArray(suppliersRefreshed) ? suppliersRefreshed : (suppliersRefreshed.results || []);
                supplierSelect.innerHTML = list.map(s => `<option value="${s.id}" ${newSupplier?.id === s.id ? 'selected' : ''}>${s.razao_social}</option>`).join('');
                if (newSupplier?.id) {
                    supplierSelect.value = String(newSupplier.id);
                }
                showToast('Fornecedor disponível para seleção.', 'success');
            });
        });

        const addItemButton = document.getElementById('add-purchase-item');
        const itemsContainer = document.getElementById('purchase-items-container');

        let debounceTimer;
        addItemButton.addEventListener('click', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const itemIndex = Date.now();
                const newItemHtml = `
                    <div class="grid grid-cols-12 gap-4 p-4 bg-gray-50 rounded-lg" id="purchase-item-${itemIndex}" data-item-key="${itemIndex}">
                        <div class="col-span-5">
                            <select name="items[${itemIndex}][produto]" class="w-full p-2 border rounded" required>
                                ${products.map(p => `<option value="${p.id}">${p.descricao}</option>`).join('')}
                            </select>
                        </div>
                        <div class="col-span-3">
                            <input type="number" name="items[${itemIndex}][quantidade]" placeholder="Qtd" class="w-full p-2 border rounded" required>
                        </div>
                        <div class="col-span-3">
                            <input type="number" step="0.01" name="items[${itemIndex}][preco_unitario]" placeholder="Preço Unit." class="w-full p-2 border rounded" required>
                        </div>
                        <div class="col-span-1 flex items-center justify-end">
                            <button type="button" onclick="removePurchaseItem(${itemIndex})" class="text-red-500 hover:text-red-700"><i class="fas fa-trash"></i></button>
                        </div>
                    </div>
                `;
                itemsContainer.insertAdjacentHTML('beforeend', newItemHtml);
            }, 1000);
        });

        window.removePurchaseItem = (index) => {
            openConfirmModal('Tem certeza que deseja remover este item da compra?', () => {
                document.getElementById(`purchase-item-${index}`).remove();
            });
        };

        document.getElementById('purchase-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const purchaseData = {
                fornecedor: formData.get('fornecedor'),
                numero_nota_fiscal: (formData.get('numero_nota_fiscal') || '').trim() || null,
                data_emissao: formData.get('data_emissao'),
                data_vencimento: formData.get('data_vencimento'),
                status_pagamento: formData.get('status_pagamento'),
                itens: []
            };

            const items = [];
            const rows = itemsContainer.querySelectorAll('[data-item-key]');
            rows.forEach((row) => {
                const key = row.getAttribute('data-item-key');
                const produto = row.querySelector(`[name="items[${key}][produto]"]`)?.value;
                const quantidade = row.querySelector(`[name="items[${key}][quantidade]"]`)?.value;
                const preco_unitario = row.querySelector(`[name="items[${key}][preco_unitario]"]`)?.value;
                if (produto && quantidade && preco_unitario) {
                    items.push({ produto, quantidade, preco_unitario });
                }
            });
            purchaseData.itens = items;

            try {
                if (purchaseData.itens.length === 0) {
                    showToast('Adicione pelo menos um item para registrar a compra.', 'error');
                    return;
                }
                const result = await api.createPurchase(purchaseData);
                const queued = resolveMutationResult(result, 'Compra registrada com sucesso!', 'Compra salva offline. Será sincronizada automaticamente quando houver internet.');
                closeModal();
                if (!queued) {
                    renderView('purchases');
                }
            } catch (error) {
                showToast('Erro ao registrar compra: ' + error.message, 'error');
            }
        });

    } catch (error) {
        showToast('Erro ao abrir formulário de compra: ' + error.message, 'error');
    }
}

async function renderFinance(container) {
    const focus = window.financeFocus || 'payable';
    const [payableSummary, receivableSummary, payableList, receivableList] = await Promise.all([
        api.getAccountsPayableSummary(),
        api.getAccountsReceivableSummary(),
        api.getAccountsPayable({ status: 'pendente' }),
        api.getAccountsReceivable({ status: 'pendente' })
    ]);

    container.innerHTML = `
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                <h3 class="text-lg font-bold text-gray-800 mb-4">Contas a Pagar</h3>
                <div class="text-3xl font-bold text-pink-600 mb-2">R$ ${parseFloat(payableSummary.total_pendente || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
                <div class="text-sm text-gray-500">Vencidas: <span class="font-bold text-red-500">${payableSummary.vencidas || 0}</span> | Próximas (7 dias): <span class="font-bold text-orange-500">${payableSummary.proximas_vencer || 0}</span></div>
            </div>
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                <h3 class="text-lg font-bold text-gray-800 mb-4">Contas a Receber</h3>
                <div class="text-3xl font-bold text-blue-600 mb-2">R$ ${parseFloat(receivableSummary.total_pendente || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
                <div class="text-sm text-gray-500">Vencidas: <span class="font-bold text-red-500">${receivableSummary.vencidas || 0}</span> | Próximas (7 dias): <span class="font-bold text-orange-500">${receivableSummary.proximas_vencer || 0}</span></div>
            </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-8">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-bold text-gray-800">Filtros Financeiros</h3>
                <div class="flex gap-2">
                    <button id="finance-tab-payable" class="px-4 py-2 rounded-xl font-bold ${focus === 'payable' ? 'bg-pastel-pink text-pink-600' : 'bg-gray-50 text-gray-600'}">Contas a Pagar</button>
                    <button id="finance-tab-receivable" class="px-4 py-2 rounded-xl font-bold ${focus === 'receivable' ? 'bg-pastel-blue text-blue-600' : 'bg-gray-50 text-gray-600'}">Contas a Receber</button>
                </div>
            </div>
            <form id="finance-filter-form" class="grid grid-cols-1 md:grid-cols-5 gap-4">
                <select name="status" class="px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">
                    <option value="">Todos os status</option>
                    <option value="pendente">Pendente</option>
                    <option value="atrasado">Não Pago</option>
                    <option value="pago">Pago</option>
                </select>
                <input type="date" name="date_from" class="px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">
                <input type="date" name="date_to" class="px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">
                <input type="number" step="0.01" name="min_valor" placeholder="Valor mín." class="px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">
                <input type="number" step="0.01" name="max_valor" placeholder="Valor máx." class="px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">
                <button type="submit" class="md:col-span-5 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-bold">Aplicar Filtros</button>
            </form>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto mb-8">
            <table class="w-full text-left">
                <thead class="bg-gray-50 border-b border-gray-100">
                    <tr>
                        <th class="px-6 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">${focus === 'payable' ? 'Fornecedor' : 'Cliente'}</th>
                        <th class="px-6 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Valor</th>
                        <th class="px-6 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Vencimento</th>
                        <th class="px-6 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Status</th>
                        <th class="px-6 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider">Histórico</th>
                        <th class="px-6 py-4 font-bold text-gray-600 uppercase text-xs tracking-wider text-right">Ações</th>
                    </tr>
                </thead>
                <tbody id="finance-table-body" class="divide-y divide-gray-50"></tbody>
            </table>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <h3 class="text-lg font-bold text-gray-800 mb-4">Fluxo de Caixa Previsto</h3>
            <div id="finance-chart" class="space-y-3"></div>
        </div>
    `;

    const tabPayable = document.getElementById('finance-tab-payable');
    const tabReceivable = document.getElementById('finance-tab-receivable');
    const filterForm = document.getElementById('finance-filter-form');
    const tableBody = document.getElementById('finance-table-body');
    const chart = document.getElementById('finance-chart');

    const renderChart = (summaryData, colorClass) => {
        const fluxo = summaryData.fluxo_caixa_previsto || [];
        if (!fluxo.length) {
            chart.innerHTML = '<p class="text-gray-400">Sem dados para o período.</p>';
            return;
        }
        const max = Math.max(...fluxo.map(f => Number(f.total || 0)), 1);
        chart.innerHTML = fluxo.map(item => {
            const value = Number(item.total || 0);
            const percent = (value / max) * 100;
            const label = new Date(item.mes).toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' });
            return `<div class="flex items-center gap-4"><span class="w-24 text-sm text-gray-500">${label}</span><div class="flex-1 bg-gray-100 rounded-full h-3 overflow-hidden"><div class="${colorClass} h-3 rounded-full" style="width:${percent}%"></div></div><span class="w-28 text-right font-bold text-gray-700">R$ ${value.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span></div>`;
        }).join('');
    };

    const renderRows = (rows, type) => {
        if (!rows.length) {
            tableBody.innerHTML = '<tr><td colspan="6" class="p-8 text-center text-gray-400">Nenhum registro encontrado.</td></tr>';
            return;
        }
        tableBody.innerHTML = rows.map(row => {
            const person = type === 'payable' ? row.fornecedor : row.cliente;
            const personName = type === 'payable'
                ? (row.fornecedor_nome || person?.razao_social)
                : (row.cliente_nome || person?.nome);
            const badge = row.status === 'pago' ? 'bg-green-100 text-green-700' : row.status === 'atrasado' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700';
            const statusLabel = row.status === 'atrasado' ? 'Não Pago' : row.status.charAt(0).toUpperCase() + row.status.slice(1);
            const historyCount = (row.historico_pagamentos || []).length;
            return `<tr>
                <td class="px-6 py-4 font-bold text-gray-800">${personName || '<span class="text-red-500">Obrigatório</span>'}</td>
                <td class="px-6 py-4 font-bold">R$ ${parseFloat(row.valor).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</td>
                <td class="px-6 py-4 text-gray-500">${new Date(row.data_vencimento).toLocaleDateString('pt-BR')}</td>
                <td class="px-6 py-4"><span class="px-3 py-1 rounded-full text-xs font-bold ${badge}">${statusLabel}</span></td>
                <td class="px-6 py-4 text-gray-500">${historyCount} eventos</td>
                <td class="px-6 py-4 text-right"><button class="px-3 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 font-bold text-sm" onclick="${type === 'payable' ? `openPayableUpdateModal(${row.id})` : `openReceivableUpdateModal(${row.id})`}">Atualizar</button></td>
            </tr>`;
        }).join('');
    };

    const loadData = async (type, filters = {}) => {
        if (type === 'payable') {
            const [list, summary] = await Promise.all([
                api.getAccountsPayable(filters),
                api.getAccountsPayableSummary()
            ]);
            renderRows(Array.isArray(list) ? list : [], 'payable');
            renderChart(summary, 'bg-pink-500');
        } else {
            const [list, summary] = await Promise.all([
                api.getAccountsReceivable(filters),
                api.getAccountsReceivableSummary()
            ]);
            renderRows(Array.isArray(list) ? list : [], 'receivable');
            renderChart(summary, 'bg-blue-500');
        }
        window.financeFocus = type;
    };

    tabPayable.addEventListener('click', async () => {
        window.financeFocus = 'payable';
        await renderView('finance');
    });
    tabReceivable.addEventListener('click', async () => {
        window.financeFocus = 'receivable';
        await renderView('finance');
    });

    filterForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(filterForm);
        const filters = {};
        for (const [key, value] of formData.entries()) {
            if (value) filters[key] = value;
        }
        await loadData(window.financeFocus || focus, filters);
    });

    await loadData(focus);
}

window.openPayableUpdateModal = async (id) => {
    const contas = await api.getAccountsPayable();
    const conta = (contas || []).find(c => c.id === id);
    if (!conta) return;
    const content = `
        <h3 class="text-2xl font-bold mb-6 text-gray-800">Atualizar Conta a Pagar</h3>
        <form id="payable-update-form" class="space-y-4">
            <select name="status" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50" required>
                <option value="pendente" ${conta.status === 'pendente' ? 'selected' : ''}>Pendente</option>
                <option value="atrasado" ${conta.status === 'atrasado' ? 'selected' : ''}>Não Pago</option>
                <option value="pago" ${conta.status === 'pago' ? 'selected' : ''}>Pago</option>
            </select>
            <input type="date" name="data_pagamento" value="${conta.data_pagamento || ''}" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">
            <input type="text" name="metodo_pagamento" value="${conta.metodo_pagamento || ''}" placeholder="Método de pagamento" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">
            <textarea name="justificativa_status" placeholder="Justificativa (obrigatória para não pago)" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">${conta.justificativa_status || ''}</textarea>
            <textarea name="observacoes" placeholder="Observações" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">${conta.observacoes || ''}</textarea>
            <div class="flex justify-end gap-3 pt-3">
                <button type="button" onclick="closeModal()" class="px-6 py-3 rounded-xl text-gray-500 hover:bg-gray-100 font-bold">Cancelar</button>
                <button type="submit" class="bg-orange-500 hover:bg-orange-600 text-white px-8 py-3 rounded-xl font-bold">Salvar</button>
            </div>
        </form>`;
    openModal(content);
    document.getElementById('payable-update-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        try {
            const result = await api.updateAccountPayable(id, data);
            const queued = resolveMutationResult(result, 'Conta a pagar atualizada com sucesso!', 'Atualização salva offline. Será sincronizada automaticamente quando houver internet.');
            closeModal();
            if (!queued) {
                const container = document.getElementById('view-container');
                await renderFinance(container);
            }
        } catch (error) {
            showToast(`Erro ao atualizar conta a pagar: ${error.message}`, 'error');
        }
    });
};

window.openReceivableUpdateModal = async (id) => {
    const contas = await api.getAccountsReceivable();
    const conta = (contas || []).find(c => c.id === id);
    if (!conta) return;
    const content = `
        <h3 class="text-2xl font-bold mb-6 text-gray-800">Atualizar Conta a Receber</h3>
        <form id="receivable-update-form" class="space-y-4">
            <select name="status" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50" required>
                <option value="pendente" ${conta.status === 'pendente' ? 'selected' : ''}>Pendente</option>
                <option value="atrasado" ${conta.status === 'atrasado' ? 'selected' : ''}>Não Pago</option>
                <option value="pago" ${conta.status === 'pago' ? 'selected' : ''}>Pago</option>
            </select>
            <input type="date" name="data_recebimento" value="${conta.data_recebimento || ''}" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">
            <input type="text" name="metodo_pagamento" value="${conta.metodo_pagamento || ''}" placeholder="Método de recebimento" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">
            <textarea name="justificativa_status" placeholder="Justificativa (obrigatória para não pago)" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">${conta.justificativa_status || ''}</textarea>
            <textarea name="observacoes" placeholder="Observações" class="w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50">${conta.observacoes || ''}</textarea>
            <div class="flex justify-end gap-3 pt-3">
                <button type="button" onclick="closeModal()" class="px-6 py-3 rounded-xl text-gray-500 hover:bg-gray-100 font-bold">Cancelar</button>
                <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold">Salvar</button>
            </div>
        </form>`;
    openModal(content);
    document.getElementById('receivable-update-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(e.target).entries());
        try {
            const result = await api.updateAccountReceivable(id, data);
            const queued = resolveMutationResult(result, 'Conta a receber atualizada com sucesso!', 'Atualização salva offline. Será sincronizada automaticamente quando houver internet.');
            closeModal();
            if (!queued) {
                const container = document.getElementById('view-container');
                await renderFinance(container);
            }
        } catch (error) {
            showToast(`Erro ao atualizar conta a receber: ${error.message}`, 'error');
        }
    });
};

// Reports Module
async function renderReports(container) {
    container.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div class="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-all cursor-pointer">
                <div class="bg-pastel-blue w-16 h-16 rounded-2xl flex items-center justify-center text-blue-600 mb-6">
                    <i class="fas fa-file-pdf text-2xl"></i>
                </div>
                <h4 class="text-xl font-bold mb-2">Relatório de Estoque</h4>
                <p class="text-gray-500 mb-6">Lista completa de produtos com níveis de estoque e valores.</p>
                <div class="flex gap-2">
                    <button onclick="downloadReport('inventory', 'excel')" class="flex-grow py-3 bg-gray-50 hover:bg-pastel-blue hover:text-blue-600 text-gray-600 font-bold rounded-xl transition-all">
                        Excel
                    </button>
                    <button onclick="downloadReport('inventory', 'pdf')" class="flex-grow py-3 bg-gray-50 hover:bg-pastel-pink hover:text-pink-600 text-gray-600 font-bold rounded-xl transition-all">
                        PDF
                    </button>
                </div>
            </div>

            <div class="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-all cursor-pointer">
                <div class="bg-pastel-green w-16 h-16 rounded-2xl flex items-center justify-center text-green-600 mb-6">
                    <i class="fas fa-file-excel text-2xl"></i>
                </div>
                <h4 class="text-xl font-bold mb-2">Relatório de Vendas</h4>
                <p class="text-gray-500 mb-6">Detalhamento de vendas por período, produto e cliente.</p>
                <div class="flex gap-2">
                    <button onclick="downloadReport('sales', 'pdf')" class="flex-grow py-3 bg-gray-50 hover:bg-pastel-green hover:text-green-600 text-gray-600 font-bold rounded-xl transition-all">
                        PDF
                    </button>
                    <button onclick="downloadReport('sales', 'excel')" class="flex-grow py-3 bg-gray-50 hover:bg-pastel-blue hover:text-blue-600 text-gray-600 font-bold rounded-xl transition-all">
                        Excel
                    </button>
                </div>
            </div>

            <div class="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-all cursor-pointer">
                <div class="bg-pastel-pink w-16 h-16 rounded-2xl flex items-center justify-center text-pink-600 mb-6">
                    <i class="fas fa-file-invoice text-2xl"></i>
                </div>
                <h4 class="text-xl font-bold mb-2">Financeiro</h4>
                <p class="text-gray-500 mb-6">Resumo de contas a pagar e receber para controle de caixa.</p>
                <div class="flex gap-2">
                    <button onclick="downloadReport('financial', 'pdf')" class="flex-grow py-3 bg-gray-50 hover:bg-pastel-pink hover:text-pink-600 text-gray-600 font-bold rounded-xl transition-all">
                        PDF
                    </button>
                    <button onclick="downloadReport('financial', 'excel')" class="flex-grow py-3 bg-gray-50 hover:bg-pastel-blue hover:text-blue-600 text-gray-600 font-bold rounded-xl transition-all">
                        Excel
                    </button>
                </div>
            </div>
        </div>
    `;
}

window.downloadReport = async (module, format) => {
    const token = localStorage.getItem('access_token');
    const url = `/api/reports/${module}/${format}/`;
    
    showToast(`Gerando relatório de ${module} em ${format.toUpperCase()}...`, 'info');
    
    try {
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) throw new Error('Falha ao gerar relatório');
        
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `relatorio_${module}_${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : 'pdf'}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('Relatório baixado com sucesso!');
    } catch (error) {
        showToast('Erro ao baixar relatório: ' + error.message, 'error');
    }
};
