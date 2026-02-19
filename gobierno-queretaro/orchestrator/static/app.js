/* PACO Admin Dashboard — Vanilla JS */

const SCOPES = [
    'water-cea', 'transport-ameq', 'education-usebeq', 'vehicles',
    'psychology-sejuve', 'women-iqm', 'culture', 'registry-rpp',
    'labor-cclq', 'housing-iveq', 'appqro', 'social-sedesoq',
    'citizen-attention',
];

class PacoAdmin {
    constructor() {
        this.apiKey = localStorage.getItem('paco_admin_key') || '';
        this.init();
    }

    init() {
        // Prompt for API key if not set
        if (!this.apiKey) {
            this.apiKey = prompt('Ingresa tu PACO Admin API Key:') || '';
            if (this.apiKey) localStorage.setItem('paco_admin_key', this.apiKey);
        }

        // Tab navigation
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });

        // Enter key on search
        document.getElementById('citizen-search')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.searchCitizens();
        });

        // Load dashboard
        this.loadDashboard();
    }

    async api(path, options = {}) {
        const resp = await fetch(`/admin${path}`, {
            ...options,
            headers: {
                'X-Admin-Key': this.apiKey,
                'Content-Type': 'application/json',
                ...(options.headers || {}),
            },
        });
        if (resp.status === 401) {
            localStorage.removeItem('paco_admin_key');
            this.apiKey = prompt('API Key inv\u00e1lida. Ingresa la correcta:') || '';
            if (this.apiKey) {
                localStorage.setItem('paco_admin_key', this.apiKey);
                return this.api(path, options);
            }
            throw new Error('No autorizado');
        }
        if (!resp.ok) throw new Error(`Error ${resp.status}: ${await resp.text()}`);
        return resp.json();
    }

    switchTab(tabId) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelector(`.tab[data-tab="${tabId}"]`).classList.add('active');

        ['dashboard', 'citizens', 'config', 'audit', 'apis'].forEach(id => {
            document.getElementById(`tab-${id}`).classList.toggle('hidden', id !== tabId);
        });

        if (tabId === 'dashboard') this.loadDashboard();
        else if (tabId === 'citizens') this.searchCitizens();
        else if (tabId === 'config') this.loadConfig();
        else if (tabId === 'audit') this.loadAudit();
        else if (tabId === 'apis') this.loadApis();
    }

    // =========================================================================
    // Dashboard
    // =========================================================================

    async loadDashboard() {
        try {
            const stats = await this.api('/memory/stats');
            document.getElementById('stat-memories').textContent = stats.total_memories || 0;
            document.getElementById('stat-summaries').textContent = stats.total_summaries || 0;
            document.getElementById('stat-profiles').textContent = stats.total_profiles || 0;
            document.getElementById('stat-pending').textContent = stats.pending_snapshots || 0;
            document.getElementById('connection-status').textContent = 'Conectado';

            const tbody = document.getElementById('scope-stats-body');
            tbody.innerHTML = '';
            const byScope = stats.memories_by_scope || {};
            for (const scope of SCOPES) {
                const count = byScope[scope] || 0;
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${scope}</strong></td>
                    <td>${count}</td>
                    <td><span class="badge ${count > 0 ? 'badge-success' : 'badge-info'}">${count > 0 ? 'activo' : 'sin datos'}</span></td>
                `;
                tbody.appendChild(tr);
            }
        } catch (e) {
            document.getElementById('connection-status').textContent = 'Error: ' + e.message;
        }
    }

    // =========================================================================
    // Citizens
    // =========================================================================

    async searchCitizens() {
        const search = document.getElementById('citizen-search').value;
        try {
            const data = await this.api(`/memory/citizens?search=${encodeURIComponent(search)}&limit=50`);
            const tbody = document.getElementById('citizens-body');
            tbody.innerHTML = '';
            for (const c of data.citizens) {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${c.contact_id}</td>
                    <td>${c.total_conversations}</td>
                    <td>${c.total_tickets}</td>
                    <td>${(c.frequent_categories || []).join(', ') || '-'}</td>
                    <td>${c.last_seen_at ? new Date(c.last_seen_at).toLocaleDateString('es-MX') : '-'}</td>
                    <td>
                        <button class="btn-outline" onclick="app.viewCitizen('${c.contact_id}')">Ver</button>
                        <button class="btn-danger" onclick="app.forgetCitizen('${c.contact_id}')">Olvidar</button>
                    </td>
                `;
                tbody.appendChild(tr);
            }
            if (data.citizens.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-dim">Sin resultados</td></tr>';
            }
        } catch (e) {
            alert('Error: ' + e.message);
        }
    }

    async viewCitizen(contactId) {
        try {
            const data = await this.api(`/memory/citizens/${contactId}`);
            const detail = document.getElementById('citizen-detail');
            detail.classList.remove('hidden');

            let html = '<div class="card mt-4">';
            html += `<h3>Detalle: ${contactId}</h3>`;

            if (data.profile) {
                const p = data.profile;
                html += `<p>Idioma: ${p.preferred_language} | Conversaciones: ${p.total_conversations} | Tickets: ${p.total_tickets}</p>`;
                html += `<p>Categor\u00edas: ${(p.frequent_categories || []).join(', ') || 'ninguna'}</p>`;
                html += `<p>Tags: ${(p.tags || []).join(', ') || 'ninguno'}</p>`;
            }

            if (data.notes && data.notes.length > 0) {
                html += '<h3 class="mt-4">Notas del Sistema</h3><ul>';
                for (const n of data.notes) {
                    html += `<li><span class="badge badge-${n.severity === 'critical' ? 'danger' : n.severity === 'warning' ? 'warning' : 'info'}">${n.severity}</span> ${n.content} <span class="text-dim">(${n.created_by})</span></li>`;
                }
                html += '</ul>';
            }

            // Scope selector for viewing agent memories
            html += '<h3 class="mt-4">Memorias por Agente</h3>';
            html += '<div class="flex gap-2 items-center mt-2">';
            html += `<select id="scope-selector">`;
            for (const s of SCOPES) {
                html += `<option value="${s}">${s}</option>`;
            }
            html += '</select>';
            html += `<button class="btn-outline" onclick="app.viewScopeMemories('${contactId}')">Ver Memorias</button>`;
            html += '</div>';
            html += '<div id="scope-memories" class="mt-2"></div>';

            html += '</div>';
            detail.innerHTML = html;
        } catch (e) {
            alert('Error: ' + e.message);
        }
    }

    async viewScopeMemories(contactId) {
        const scope = document.getElementById('scope-selector').value;
        const container = document.getElementById('scope-memories');
        try {
            const data = await this.api(`/memory/scopes/${scope}/citizens/${contactId}`);
            let html = '<table><thead><tr><th>Tipo</th><th>Contenido</th><th>Importancia</th><th>Tags</th></tr></thead><tbody>';
            const memories = data.memories || [];
            if (memories.length === 0) {
                html += '<tr><td colspan="4" class="text-dim">Sin memorias para este scope</td></tr>';
            }
            for (const m of memories) {
                html += `<tr><td>${m.memory_type}</td><td>${m.content}</td><td>${m.importance}</td><td>${(m.tags || []).join(', ')}</td></tr>`;
            }
            html += '</tbody></table>';
            container.innerHTML = html;
        } catch (e) {
            container.innerHTML = `<p class="text-dim">Error: ${e.message}</p>`;
        }
    }

    async forgetCitizen(contactId) {
        if (!confirm(`\u00bfOlvidar completamente al ciudadano ${contactId}? Esta acci\u00f3n es IRREVERSIBLE.`)) return;
        try {
            await this.api(`/memory/citizens/${contactId}?performed_by=admin`, { method: 'DELETE' });
            alert('Ciudadano olvidado exitosamente.');
            this.searchCitizens();
        } catch (e) {
            alert('Error: ' + e.message);
        }
    }

    // =========================================================================
    // Configuration
    // =========================================================================

    async loadConfig() {
        try {
            const config = await this.api('/memory/config');
            const form = document.getElementById('global-config-form');
            form.innerHTML = `
                <div class="flex gap-4 items-center mt-2">
                    <label>Memoria Habilitada:</label>
                    <label class="toggle">
                        <input type="checkbox" id="cfg-enabled" ${config.enabled ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="flex gap-4 items-center mt-2">
                    <label>Resumir Conversaciones:</label>
                    <label class="toggle">
                        <input type="checkbox" id="cfg-summarization" ${config.summarization?.enabled ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="flex gap-4 items-center mt-2">
                    <label>M\u00e1x. Memorias en Prompt:</label>
                    <input type="number" id="cfg-max-prompt" value="${config.injection?.max_in_prompt || 5}" min="0" max="20" style="width:80px">
                </div>
                <div class="flex gap-4 items-center mt-2">
                    <label>Retenci\u00f3n de Memorias (d\u00edas):</label>
                    <input type="number" id="cfg-retention" value="${config.retention?.memory_days || 180}" min="1" style="width:80px">
                </div>
                <div class="flex gap-4 items-center mt-2">
                    <label>Permitir Eliminaci\u00f3n (GDPR):</label>
                    <label class="toggle">
                        <input type="checkbox" id="cfg-deletion" ${config.privacy?.allow_deletion ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                </div>
                <button class="btn-primary mt-4" onclick="app.saveGlobalConfig()">Guardar Configuraci\u00f3n Global</button>
            `;

            // Per-scope config
            const list = document.getElementById('scope-config-list');
            list.innerHTML = '';
            for (const scope of SCOPES) {
                let scopeConfig;
                try {
                    scopeConfig = await this.api(`/memory/scopes/${scope}/config`);
                } catch {
                    scopeConfig = { enabled: true };
                }
                const item = document.createElement('div');
                item.className = 'scope-item';
                item.innerHTML = `
                    <div>
                        <div class="name">${scope}</div>
                        <div class="stats">${scopeConfig.enabled ? 'Habilitado' : 'Deshabilitado'}</div>
                    </div>
                    <label class="toggle">
                        <input type="checkbox" data-scope="${scope}" ${scopeConfig.enabled ? 'checked' : ''} onchange="app.toggleScope('${scope}', this.checked)">
                        <span class="slider"></span>
                    </label>
                `;
                list.appendChild(item);
            }
        } catch (e) {
            alert('Error cargando config: ' + e.message);
        }
    }

    async saveGlobalConfig() {
        const config = {
            enabled: document.getElementById('cfg-enabled').checked,
            summarization: {
                enabled: document.getElementById('cfg-summarization').checked,
            },
            injection: {
                max_in_prompt: parseInt(document.getElementById('cfg-max-prompt').value),
            },
            retention: {
                memory_days: parseInt(document.getElementById('cfg-retention').value),
            },
            privacy: {
                allow_deletion: document.getElementById('cfg-deletion').checked,
            },
        };
        try {
            await this.api('/memory/config', {
                method: 'PUT',
                body: JSON.stringify({ config, updated_by: 'admin-ui' }),
            });
            alert('Configuraci\u00f3n guardada.');
        } catch (e) {
            alert('Error: ' + e.message);
        }
    }

    async toggleScope(scope, enabled) {
        try {
            await this.api(`/memory/scopes/${scope}/config`, {
                method: 'PUT',
                body: JSON.stringify({ config: { enabled }, updated_by: 'admin-ui' }),
            });
        } catch (e) {
            alert('Error: ' + e.message);
        }
    }

    // =========================================================================
    // Audit
    // =========================================================================

    async loadAudit() {
        const contactId = document.getElementById('audit-contact').value;
        const action = document.getElementById('audit-action').value;
        let query = '/memory/audit?limit=50';
        if (contactId) query += `&contact_id=${encodeURIComponent(contactId)}`;
        if (action) query += `&action=${encodeURIComponent(action)}`;

        try {
            const data = await this.api(query);
            const tbody = document.getElementById('audit-body');
            tbody.innerHTML = '';
            for (const e of data.entries) {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${e.created_at ? new Date(e.created_at).toLocaleString('es-MX') : '-'}</td>
                    <td><span class="badge badge-info">${e.action}</span></td>
                    <td>${e.scope_id || '-'}</td>
                    <td>${e.citizen_contact_id || '-'}</td>
                    <td>${e.performed_by || '-'}</td>
                    <td class="text-dim text-sm">${JSON.stringify(e.details || {}).substring(0, 80)}</td>
                `;
                tbody.appendChild(tr);
            }
            if (data.entries.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-dim">Sin registros</td></tr>';
            }
        } catch (e) {
            alert('Error: ' + e.message);
        }
    }

    // =========================================================================
    // Maintenance
    // =========================================================================

    async triggerCleanup() {
        try {
            const r = await this.api('/memory/maintenance/cleanup', { method: 'POST' });
            alert(`Limpieza completada: ${r.deleted} registros eliminados.`);
            this.loadDashboard();
        } catch (e) {
            alert('Error: ' + e.message);
        }
    }

    async triggerSummarize() {
        try {
            const r = await this.api('/memory/maintenance/summarize-now', { method: 'POST' });
            alert(`Resumen batch completado: ${JSON.stringify(r)}`);
            this.loadDashboard();
        } catch (e) {
            alert('Error: ' + e.message);
        }
    }

    // =========================================================================
    // APIs
    // =========================================================================

    async loadApis() {
        try {
            const data = await this.api('/apis');
            const apis = data.apis;

            // Stat cards
            document.getElementById('stat-apis-total').textContent = apis.length;
            document.getElementById('stat-apis-active').textContent = apis.filter(a => a.status === 'active').length;
            document.getElementById('stat-apis-mocked').textContent = apis.filter(a => a.status === 'mocked').length;
            document.getElementById('stat-apis-planned').textContent = apis.filter(a => a.status === 'planned').length;

            // Table
            const tbody = document.getElementById('apis-body');
            tbody.innerHTML = '';
            for (const api of apis) {
                const statusClass = api.status === 'active' ? 'badge-success' : api.status === 'mocked' ? 'badge-info' : 'badge-warning';
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${api.id}</strong></td>
                    <td>${api.name}</td>
                    <td><span class="badge badge-info">${api.protocol}</span></td>
                    <td>${api.auth_type}</td>
                    <td>${api.operations}</td>
                    <td><span class="badge ${statusClass}">${api.status}</span></td>
                    <td>
                        <button class="btn-outline" onclick="app.viewApi('${api.id}')">Detalle</button>
                        <button class="btn-outline" id="health-btn-${api.id}" onclick="app.checkApiHealth('${api.id}', this)">Health</button>
                    </td>
                `;
                tbody.appendChild(tr);
            }
            if (apis.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-dim">Sin APIs registradas</td></tr>';
            }

            // Hide detail when reloading list
            document.getElementById('api-detail').classList.add('hidden');
        } catch (e) {
            alert('Error cargando APIs: ' + e.message);
        }
    }

    async viewApi(apiId) {
        try {
            const data = await this.api(`/apis/${apiId}`);
            const detail = document.getElementById('api-detail');
            detail.classList.remove('hidden');

            const statusClass = data.status === 'active' ? 'badge-success' : data.status === 'mocked' ? 'badge-info' : 'badge-warning';
            const cbState = data.circuit_breaker?.state || 'closed';
            const cbClass = cbState === 'closed' ? 'badge-success' : cbState === 'half_open' ? 'badge-warning' : 'badge-danger';

            let html = '<div class="card mt-4">';
            html += `<h3>${data.name} <span class="badge ${statusClass}">${data.status}</span></h3>`;
            html += `<p>${data.description}</p>`;
            html += `<p>Protocolo: <span class="badge badge-info">${data.protocol}</span> | Auth: ${data.auth_type} | Timeout: ${data.timeout_ms}ms</p>`;
            html += `<p>Circuit Breaker: <span class="badge ${cbClass}">${cbState}</span> — Failures: ${data.circuit_breaker?.failures || 0}, Successes: ${data.circuit_breaker?.successes || 0}</p>`;

            // Operations table
            html += '<h3 class="mt-4">Operaciones</h3>';
            html += '<table><thead><tr><th>ID</th><th>Descripci\u00f3n</th><th>M\u00e9todo</th><th>Path</th><th>Par\u00e1metros</th><th>Acciones</th></tr></thead><tbody>';
            for (const op of data.operations) {
                const paramsStr = (op.input_params || []).join(', ') || '-';
                html += `<tr>
                    <td><strong>${op.id}</strong></td>
                    <td>${op.description}</td>
                    <td><span class="badge badge-info">${op.method}</span></td>
                    <td class="text-dim text-sm">${op.path || '-'}</td>
                    <td class="text-sm">${paramsStr}</td>
                    <td><button class="btn-outline" onclick="app.testOperation('${apiId}', '${op.id}', ${JSON.stringify(op.input_params || []).replace(/"/g, '&quot;')})">Probar</button></td>
                </tr>`;
            }
            html += '</tbody></table>';

            // Schema preview
            if (data.schema) {
                html += '<h3 class="mt-4">Schema</h3>';
                html += `<pre style="max-height:300px;overflow:auto;background:#1a1a2e;padding:12px;border-radius:8px;font-size:12px">${JSON.stringify(data.schema, null, 2)}</pre>`;
            }

            // Test result area
            html += '<div id="api-test-result" class="mt-4"></div>';
            html += '</div>';
            detail.innerHTML = html;
        } catch (e) {
            alert('Error: ' + e.message);
        }
    }

    async checkApiHealth(apiId, btn) {
        btn.disabled = true;
        btn.textContent = '...';
        try {
            const data = await this.api(`/apis/${apiId}/health`);
            const healthy = data.healthy;
            const badgeClass = healthy ? 'badge-success' : 'badge-danger';
            const latency = data.latency_ms !== null ? `${data.latency_ms}ms` : '-';
            const label = data.status === 'mocked' ? 'mock' : healthy ? 'ok' : data.status;
            btn.outerHTML = `<span class="badge ${badgeClass}">${label} ${latency}</span>`;
        } catch (e) {
            btn.outerHTML = `<span class="badge badge-danger">error</span>`;
        }
    }

    async testOperation(apiId, opId, inputParams) {
        const params = {};
        for (const p of inputParams) {
            const val = prompt(`Par\u00e1metro "${p}":`);
            if (val === null) return; // User cancelled
            params[p] = val;
        }

        const resultDiv = document.getElementById('api-test-result');
        if (resultDiv) resultDiv.innerHTML = '<p class="text-dim">Ejecutando...</p>';

        try {
            const data = await this.api(`/apis/${apiId}/test`, {
                method: 'POST',
                body: JSON.stringify({ operation_id: opId, params }),
            });

            if (!resultDiv) return;
            if (data.success) {
                const formatted = data.format === 'xml'
                    ? data.result
                    : JSON.stringify(data.result, null, 2);
                resultDiv.innerHTML = `
                    <div class="card">
                        <h3>Resultado: ${opId} <span class="badge badge-success">OK</span></h3>
                        <pre style="max-height:300px;overflow:auto;background:#1a1a2e;padding:12px;border-radius:8px;font-size:12px">${formatted.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
                    </div>`;
            } else {
                resultDiv.innerHTML = `
                    <div class="card">
                        <h3>Resultado: ${opId} <span class="badge badge-danger">Error</span></h3>
                        <p>${data.error}</p>
                    </div>`;
            }
        } catch (e) {
            if (resultDiv) resultDiv.innerHTML = `<div class="card"><p class="badge-danger">Error: ${e.message}</p></div>`;
        }
    }
}

const app = new PacoAdmin();
