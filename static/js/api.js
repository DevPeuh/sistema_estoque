const API_BASE_URL = '/api';
const OFFLINE_QUEUE_KEY = 'offline_queue';

const api = {
    async request(endpoint, options = {}) {
        const requestOptions = { ...options };
        const skipOfflineQueue = requestOptions._skipOfflineQueue === true;
        const isSyncReplay = requestOptions._isSyncReplay === true;
        delete requestOptions._skipOfflineQueue;
        delete requestOptions._isSyncReplay;

        if (!navigator.onLine && requestOptions.method !== 'GET' && requestOptions.method && !skipOfflineQueue) {
            const queuedItem = this.queueOfflineRequest(endpoint, requestOptions);
            showToast('Sem conexão. A operação foi salva e será sincronizada quando houver internet.', 'info');
            return { offline: true, queued: true, queue_item_id: queuedItem.id };
        }

        const token = localStorage.getItem('access_token');
        const defaultHeaders = {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        };

        const config = {
            ...requestOptions,
            headers: {
                ...defaultHeaders,
                ...requestOptions.headers
            }
        };

        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
            
            if (response.status === 401 && !endpoint.includes('/token/')) {
                // Token expired or invalid, try to refresh
                const refreshed = await this.refreshToken();
                if (refreshed) {
                    return this.request(endpoint, options);
                } else {
                    if (isSyncReplay) {
                        throw new Error('Sessão expirada para sincronização. Faça login novamente e tente reenviar as pendências.');
                    }
                    this.logout();
                    throw new Error('Sessão expirada. Faça login novamente.');
                }
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const parseErrors = (data) => {
                    if (!data) return null;
                    if (typeof data === 'string') return data;
                    if (Array.isArray(data)) return data.join(' ');
                    if (typeof data === 'object') {
                        if (data.detail) return parseErrors(data.detail);
                        if (data.message) return parseErrors(data.message);
                        const messages = Object.values(data).map(v => parseErrors(v)).filter(Boolean);
                        return messages.length ? messages.join(' ') : null;
                    }
                    return null;
                };
                throw new Error(parseErrors(errorData) || `Erro ${response.status}: ${response.statusText}`);
            }

            if (response.status === 204) return null;
            return await response.json();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    },

    async login(username, password) {
        const data = await this.request('/token/', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
        
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        localStorage.setItem('username', username);
        return data;
    },

    async refreshToken() {
        const refresh = localStorage.getItem('refresh_token');
        if (!refresh) return false;

        try {
            const response = await fetch(`${API_BASE_URL}/token/refresh/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh })
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('access_token', data.access);
                return true;
            }
            return false;
        } catch (error) {
            return false;
        }
    },

    logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('username');
        window.dispatchEvent(new CustomEvent('auth-change'));
    },

    isAuthenticated() {
        return !!localStorage.getItem('access_token');
    },

    // Sincronização Off-line
    getOfflineQueue() {
        return JSON.parse(localStorage.getItem(OFFLINE_QUEUE_KEY) || '[]');
    },

    saveOfflineQueue(queue) {
        localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue));
        this.dispatchOfflineQueueChanged();
    },

    dispatchOfflineQueueChanged() {
        window.dispatchEvent(new CustomEvent('offline-queue-changed', {
            detail: this.getOfflineQueueSummary()
        }));
    },

    getOfflineQueueSummary() {
        const queue = this.getOfflineQueue();
        const totals = queue.reduce((acc, item) => {
            const status = item.status || 'pending';
            acc.total += 1;
            acc[status] = (acc[status] || 0) + 1;
            return acc;
        }, { total: 0, pending: 0, syncing: 0, failed: 0 });
        return totals;
    },

    getOfflineQueueItems() {
        return this.getOfflineQueue();
    },

    generateRequestId() {
        if (window.crypto?.randomUUID) {
            return window.crypto.randomUUID();
        }
        return `req_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
    },

    normalizeQueuedRequest(endpoint, options) {
        const normalizedOptions = {
            ...options,
            headers: {
                ...(options.headers || {})
            }
        };
        const method = (normalizedOptions.method || 'GET').toUpperCase();
        const headerRequestId = normalizedOptions.headers['X-Request-ID'] || normalizedOptions.headers['x-request-id'];
        let requestId = headerRequestId || this.generateRequestId();
        const hasJsonBody = typeof normalizedOptions.body === 'string' && normalizedOptions.body.trim().startsWith('{');
        if (hasJsonBody) {
            try {
                const bodyData = JSON.parse(normalizedOptions.body);
                if (bodyData.request_id) {
                    requestId = bodyData.request_id;
                } else {
                    bodyData.request_id = requestId;
                    normalizedOptions.body = JSON.stringify(bodyData);
                }
            } catch (error) {
                requestId = headerRequestId || requestId;
            }
        }
        normalizedOptions.headers['X-Request-ID'] = requestId;
        return { endpoint, options: normalizedOptions, method, requestId };
    },

    queueOfflineRequest(endpoint, options) {
        const queue = this.getOfflineQueue();
        const normalized = this.normalizeQueuedRequest(endpoint, options);
        const existing = queue.find(item => item.id === normalized.requestId);
        if (existing) {
            return existing;
        }
        const now = new Date().toISOString();
        const queueItem = {
            id: normalized.requestId,
            endpoint: normalized.endpoint,
            method: normalized.method,
            options: normalized.options,
            status: 'pending',
            attempts: 0,
            created_at: now,
            updated_at: now,
            last_error: null
        };
        queue.push(queueItem);
        this.saveOfflineQueue(queue);
        return queueItem;
    },

    async syncOfflineData() {
        if (!navigator.onLine) {
            showToast('Você ainda está offline. Conecte-se para sincronizar.', 'warning');
            return { success: 0, failed: 0 };
        }

        const queue = this.getOfflineQueue();
        if (queue.length === 0) return;

        showToast(`Sincronizando ${queue.length} operações pendentes...`, 'info');

        let successCount = 0;
        const updatedQueue = [...queue];
        for (let index = 0; index < updatedQueue.length; index += 1) {
            const item = updatedQueue[index];
            item.status = 'syncing';
            item.attempts = (item.attempts || 0) + 1;
            item.updated_at = new Date().toISOString();
            item.last_error = null;
            this.saveOfflineQueue(updatedQueue);
            try {
                await this.request(item.endpoint, {
                    ...item.options,
                    _skipOfflineQueue: true,
                    _isSyncReplay: true
                });
                successCount += 1;
                window.dispatchEvent(new CustomEvent('offline-item-synced', { detail: { id: item.id } }));
                showToast(`Pendência ${successCount}/${queue.length} sincronizada com sucesso.`, 'success');
                updatedQueue.splice(index, 1);
                index -= 1;
                this.saveOfflineQueue(updatedQueue);
            } catch (err) {
                console.error('Falha ao sincronizar item:', item, err);
                item.status = 'failed';
                item.updated_at = new Date().toISOString();
                item.last_error = err.message || 'Erro desconhecido';
                this.saveOfflineQueue(updatedQueue);
            }
        }

        const remaining = this.getOfflineQueue();
        if (remaining.length === 0) {
            showToast('Sincronização concluída com sucesso!', 'success');
            if (window.renderView && document.querySelector('.sidebar-active')) {
                const activeView = document.querySelector('.sidebar-active').getAttribute('data-view');
                window.renderView(activeView);
            }
        } else {
            showToast(`${remaining.length} pendência(s) não puderam ser sincronizadas.`, 'error');
        }
        return { success: successCount, failed: remaining.length };
    },

    // Dashboard
    async getDashboardStats() {
        return await this.request('/dashboard/stats/');
    },
    async getSystemHealth() {
        return await this.request('/dashboard/health/');
    },

    // Produto
    async getProducts() {
        return await this.request('/produtos/');
    },
    async getProduct(id) {
        return await this.request(`/produtos/${id}/`);
    },
    async createProduct(data) {
        return await this.request('/produtos/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    async updateProduct(id, data) {
        return await this.request(`/produtos/${id}/`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    async deleteProduct(id) {
        return await this.request(`/produtos/${id}/`, {
            method: 'DELETE'
        });
    },

    // Categoria
    async getCategories() {
        return await this.request('/categorias/');
    },
    async createCategory(data) {
        return await this.request('/categorias/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    async deleteCategory(id) {
        return await this.request(`/categorias/${id}/`, {
            method: 'DELETE'
        });
    },
    async getUnits() {
        return await this.request('/unidades-de-medida/');
    },

    async getSuppliers() {
        return await this.request('/compras/fornecedores/');
    },
    async createSupplier(data) {
        return await this.request('/compras/fornecedores/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    async deleteSupplier(id) {
        return await this.request(`/compras/fornecedores/${id}/`, {
            method: 'DELETE'
        });
    },

    // Cliente
    async getClients() {
        return await this.request('/vendas/clientes/');
    },
    async getClient(id) {
        return await this.request(`/vendas/clientes/${id}/`);
    },
    async createClient(data) {
        return await this.request('/vendas/clientes/', { method: 'POST', body: JSON.stringify(data) });
    },
    async updateClient(id, data) {
        return await this.request(`/vendas/clientes/${id}/`, { method: 'PUT', body: JSON.stringify(data) });
    },
    async deleteClient(id) {
        return await this.request(`/vendas/clientes/${id}/`, { method: 'DELETE' });
    },

    // venda
    async getSales() {
        return await this.request('/vendas/vendas/');
    },
    async createSale(data) {
        return await this.request('/vendas/vendas/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // Compra
    async getPurchases() {
        return await this.request('/compras/compras/');
    },
    async createPurchase(data) {
        return await this.request('/compras/compras/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // Contas a Pagar
    async getAccountsPayable(filters = {}) {
        const params = new URLSearchParams(filters).toString();
        const query = params ? `?${params}` : '';
        return await this.request(`/compras/contas-pagar/${query}`);
    },
    async updateAccountPayable(id, data) {
        return await this.request(`/compras/contas-pagar/${id}/`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },
    async getAccountsPayableSummary() {
        return await this.request('/compras/contas-pagar/summary/');
    },

    // Contas a Receber
    async getAccountsReceivable(filters = {}) {
        const params = new URLSearchParams(filters).toString();
        const query = params ? `?${params}` : '';
        return await this.request(`/vendas/contas-receber/${query}`);
    },
    async updateAccountReceivable(id, data) {
        return await this.request(`/vendas/contas-receber/${id}/`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },
    async getAccountsReceivableSummary() {
        return await this.request('/vendas/contas-receber/summary/');
    },

    // Relatório
    async getReports(type) {
        return await this.request(`/reports/${type}/`);
    }
};
