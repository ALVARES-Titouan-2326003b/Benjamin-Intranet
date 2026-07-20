/**
 * Calendrier avec activités - Version avec Tooltips
 */

(function() {


    const TYPES_CONFIG = {
        'vente': { nom: 'Vente', couleur: '#27ae60' },
        'location': { nom: 'Location', couleur: '#3498db' },
        'compromis': { nom: 'Compromis', couleur: '#e74c3c' },
        'visite': { nom: 'Visite', couleur: '#f39c12' },
        'relance': { nom: 'Relance', couleur: '#9b59b6' },
        'autre': { nom: 'Autre', couleur: '#95a5a6' }
    };

    const STATUTS_CONFIG = {
        'todo': { nom: 'À faire', couleur: '#64748b' },
        'in_progress': { nom: 'En cours', couleur: '#2563eb' },
        'done': { nom: 'Terminé', couleur: '#16a34a' },
        'cancelled': { nom: 'Annulé', couleur: '#dc2626' }
    };

    const PRIORITES_CONFIG = {
        'low': { nom: 'Basse', couleur: '#64748b' },
        'normal': { nom: 'Normale', couleur: '#0ea5e9' },
        'high': { nom: 'Haute', couleur: '#f97316' },
        'urgent': { nom: 'Urgente', couleur: '#dc2626' }
    };

    /* Palette cyclique pour les dossiers */
    const DOSSIER_PALETTE = [
        '#0ea5e9','#6366f1','#ec4899','#14b8a6','#f97316',
        '#84cc16','#8b5cf6','#06b6d4','#f59e0b','#10b981',
        '#ef4444','#64748b'
    ];

    const MOIS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"];



    let state = {
        date: new Date(),
        currYear: new Date().getFullYear(),
        currMonth: new Date().getMonth(),
        activites: [],
        filtresTypes: {},
        filtresDossiers: {},
        filtresStatuts: {},
        filtresPriorites: {},
        filtresResponsables: {},
        filtreClient: '',
        filtreContact: '',
        filtersCollapsed: true,
        calendarScope: 'mine',
        calendarReadOnly: false
    };
    window.adminCalendarState = state;

    const calendarConfig = document.getElementById('admin-calendar-config');
    if (calendarConfig?.dataset?.defaultScope) {
        state.calendarScope = calendarConfig.dataset.defaultScope;
    }

    // Éléments DOM
    const days = document.querySelector(".days");
    const currentDate = document.querySelector(".current-date");
    const prevNextIcon = document.querySelectorAll(".icons span");

    // Tooltip
    let tooltipElement = null;

    function escapeHtml(value) {
        return String(value || '').replace(/[&<>"']/g, char => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[char]));
    }



    function createTooltip() {
        if (tooltipElement) return;

        tooltipElement = document.createElement('div');
        tooltipElement.className = 'activity-tooltip';
        document.body.appendChild(tooltipElement);
    }

    function showTooltip(dateStr, mouseEvent) {
        if (!tooltipElement) createTooltip();

        const activites = getActivitiesForDate(dateStr);
        if (activites.length === 0) { hideTooltip(); return; }

        let html = `<div class="activity-tooltip-header">`;
        html += ` ${formatDateForDisplay(dateStr)} — ${activites.length} activité${activites.length > 1 ? 's' : ''}`;
        html += `</div>`;

        activites.forEach(act => {
            const typeKey   = (act.type || 'autre').toLowerCase();
            const config    = TYPES_CONFIG[typeKey] || TYPES_CONFIG['autre'];
            const nomDossier = act.dossier_nom || act.dossier;
            const titre = act.titre || config.nom;
            const priorityColor = act.priority_color || PRIORITES_CONFIG[act.priorite || 'normal'].couleur;

            html += `<div class="activity-tooltip-item" data-type="${typeKey}">`;
            html += `  <div class="activity-tooltip-type">`;
            html += `    <span class="activity-tooltip-color" style="background:${priorityColor}"></span>`;
            html += `    <span class="activity-tooltip-type-label">${escapeHtml(titre)}</span>`;
            html += `  </div>`;
            html += `  <div class="activity-tooltip-dossier">📁 ${escapeHtml(nomDossier)}</div>`;
            if (act.time || act.duree_label) {
                const creneau = `${act.time || ''}${act.end_time ? `-${act.end_time}` : ''}${act.duree_label ? ` · ${act.duree_label}` : ''}`;
                html += `  <div class="activity-tooltip-dossier-nom">${escapeHtml(creneau)}</div>`;
            }
            html += `  <div class="activity-tooltip-dossier-nom">${escapeHtml(act.statut_label || '')} · ${escapeHtml(act.priorite_label || '')}</div>`;
            if (act.is_overdue) {
                html += `  <div class="activity-tooltip-description" style="color:#dc2626;font-weight:700;">En retard</div>`;
            }
            if (act.dossier_nom && act.dossier_nom !== act.dossier) {
                html += `  <div class="activity-tooltip-dossier-nom">${escapeHtml(act.dossier)}</div>`;
            }
            if (act.commentaire) {
                html += `  <div class="activity-tooltip-description">${escapeHtml(act.commentaire)}</div>`;
            }
            html += `</div>`;
        });

        tooltipElement.innerHTML = html;
        positionTooltip(mouseEvent);
        tooltipElement.classList.add('visible');
    }

    function positionTooltip(mouseEvent) {
        if (!tooltipElement) return;

        const tooltipRect = tooltipElement.getBoundingClientRect();
        const padding = 15;

        let left = mouseEvent.clientX + padding;
        let top  = mouseEvent.clientY + padding;

        if (left + tooltipRect.width > window.innerWidth) {
            left = mouseEvent.clientX - tooltipRect.width - padding;
        }
        if (top + tooltipRect.height > window.innerHeight) {
            top = mouseEvent.clientY - tooltipRect.height - padding;
        }

        left = Math.max(padding, left);
        top  = Math.max(padding, top);

        tooltipElement.style.left = `${left}px`;
        tooltipElement.style.top  = `${top}px`;
    }

    function hideTooltip() {
        if (tooltipElement) {
            tooltipElement.classList.remove('visible');
        }
    }

    function formatDateForDisplay(dateStr) {
        const [year, month, day] = dateStr.split('-');
        return `${day}/${month}/${year}`;
    }


    async function loadActivities(month, year) {
        try {
            console.log(` Chargement activités pour ${month + 1}/${year}`);

            const params = new URLSearchParams({
                month: String(month + 1),
                year: String(year),
                calendar_scope: state.calendarScope
            });
            const response = await fetch(`/api/calendar-activities/?${params.toString()}`);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                state.activites = data.activites;
                state.calendarReadOnly = !!data.read_only;
                console.log(` ${data.activites.length} activités chargées`);

                initFilters();
                updateCalendarModeUi();
                renderCalendar();
            } else {
                console.error(' Erreur API:', data.message);
                state.activites = [];
                renderCalendar();
            }
        } catch (error) {
            console.error(' Erreur chargement activités:', error);
            state.activites = [];
            renderCalendar();
        }
    }


    function initFilters() {
        const typesUniques    = [...new Set(state.activites.map(a => a.type))];
        const dossiersUniques = [...new Set(state.activites.map(a => a.dossier))];
        const statutsUniques  = [...new Set(state.activites.map(a => a.statut || 'todo'))];
        const prioritesUniques = [...new Set(state.activites.map(a => a.priorite || 'normal'))];
        const responsablesUniques = [...new Set(state.activites.map(a => a.responsable_id || '').filter(Boolean))];

        // Préserver l'état existant, ne mettre true que pour les nouvelles entrées
        const prevTypes    = state.filtresTypes    || {};
        const prevDossiers = state.filtresDossiers || {};
        const prevStatuts  = state.filtresStatuts  || {};
        const prevPriorites = state.filtresPriorites || {};
        const prevResponsables = state.filtresResponsables || {};

        state.filtresTypes = {};
        typesUniques.forEach(type => {
            state.filtresTypes[type] = (type in prevTypes) ? prevTypes[type] : true;
        });

        state.filtresDossiers = {};
        dossiersUniques.forEach(dossier => {
            state.filtresDossiers[dossier] = (dossier in prevDossiers) ? prevDossiers[dossier] : true;
        });

        state.filtresStatuts = {};
        statutsUniques.forEach(statut => {
            state.filtresStatuts[statut] = (statut in prevStatuts) ? prevStatuts[statut] : true;
        });

        state.filtresPriorites = {};
        prioritesUniques.forEach(priorite => {
            state.filtresPriorites[priorite] = (priorite in prevPriorites) ? prevPriorites[priorite] : true;
        });

        state.filtresResponsables = {};
        responsablesUniques.forEach(responsable => {
            state.filtresResponsables[responsable] = (responsable in prevResponsables) ? prevResponsables[responsable] : true;
        });

        renderFilters(typesUniques, dossiersUniques, statutsUniques, prioritesUniques, responsablesUniques);
    }

    /* ── Construit le texte du badge résumé ── */
    function buildFilterSummary() {
        const totalTypes    = Object.keys(state.filtresTypes).length;
        const activeTypes   = Object.values(state.filtresTypes).filter(Boolean).length;
        const totalDoss     = Object.keys(state.filtresDossiers).length;
        const activeDoss    = Object.values(state.filtresDossiers).filter(Boolean).length;
        const totalStatuts  = Object.keys(state.filtresStatuts).length;
        const activeStatuts = Object.values(state.filtresStatuts).filter(Boolean).length;
        const totalPriorites = Object.keys(state.filtresPriorites).length;
        const activePriorites = Object.values(state.filtresPriorites).filter(Boolean).length;

        if (totalTypes === 0 && totalDoss === 0 && totalStatuts === 0 && totalPriorites === 0) return '';

        if (activeTypes === totalTypes && activeDoss === totalDoss
            && activeStatuts === totalStatuts && activePriorites === totalPriorites
            && !state.filtreClient && !state.filtreContact) {
            return 'Tout activé';
        }
        if (activeTypes === 0 && activeDoss === 0 && activeStatuts === 0 && activePriorites === 0) {
            return 'Aucun filtre actif';
        }

        const parts = [];
        if (totalTypes > 0)  parts.push(`${activeTypes}/${totalTypes} types`);
        if (totalDoss  > 0)  parts.push(`${activeDoss}/${totalDoss} dossiers`);
        if (totalStatuts > 0) parts.push(`${activeStatuts}/${totalStatuts} statuts`);
        if (totalPriorites > 0) parts.push(`${activePriorites}/${totalPriorites} priorités`);
        if (state.filtreClient) parts.push('client');
        if (state.filtreContact) parts.push('contact');
        return parts.join(' · ');
    }

    /* ── Met à jour uniquement le badge sans re-rendre tout le bloc ── */
    function updateFilterSummary() {
        const badge = document.getElementById('filter-summary-badge');
        if (!badge) return;

        const text = buildFilterSummary();
        badge.textContent = text;

        const totalTypes  = Object.keys(state.filtresTypes).length;
        const activeTypes = Object.values(state.filtresTypes).filter(Boolean).length;
        const totalDoss   = Object.keys(state.filtresDossiers).length;
        const activeDoss  = Object.values(state.filtresDossiers).filter(Boolean).length;
        const totalStatuts = Object.keys(state.filtresStatuts).length;
        const activeStatuts = Object.values(state.filtresStatuts).filter(Boolean).length;
        const totalPriorites = Object.keys(state.filtresPriorites).length;
        const activePriorites = Object.values(state.filtresPriorites).filter(Boolean).length;

        badge.className = 'filter-summary-badge';
        if (activeTypes === totalTypes && activeDoss === totalDoss
            && activeStatuts === totalStatuts && activePriorites === totalPriorites
            && !state.filtreClient && !state.filtreContact) {
            badge.classList.add('all-active');
        } else if (activeTypes === 0 && activeDoss === 0 && activeStatuts === 0 && activePriorites === 0) {
            badge.classList.add('none-active');
        }
    }

    function updateCalendarExportLink() {
        const link = document.getElementById('calendar-export-ics');
        if (!link) return;

        const params = new URLSearchParams({
            month: String(state.currMonth + 1),
            year: String(state.currYear),
            calendar_scope: state.calendarScope
        });
        link.href = `/administratif/calendrier/export.ics?${params.toString()}`;
        link.setAttribute('download', `calendrier_administratif_${state.currYear}_${String(state.currMonth + 1).padStart(2, '0')}.ics`);
    }

    function updateCalendarModeUi() {
        document.querySelectorAll('[data-calendar-scope]').forEach(button => {
            button.classList.toggle('active', button.dataset.calendarScope === state.calendarScope);
        });

        document.querySelectorAll('.calendar-write-actions').forEach(element => {
            if (!element.dataset.defaultDisplay) {
                element.dataset.defaultDisplay = element.style.display || '';
            }
            element.style.display = state.calendarReadOnly ? 'none' : element.dataset.defaultDisplay;
        });

        const modal = document.getElementById('activity-modal');
        if (modal && state.calendarReadOnly) {
            modal.style.display = 'none';
        }
        updateCalendarExportLink();
    }
    window.updateCalendarModeUi = updateCalendarModeUi;

    function setupCalendarScopeButtons() {
        document.querySelectorAll('[data-calendar-scope]').forEach(button => {
            button.addEventListener('click', () => {
                const nextScope = button.dataset.calendarScope || 'mine';
                if (nextScope === state.calendarScope) return;
                state.calendarScope = nextScope;
                hideTooltip();
                loadActivities(state.currMonth, state.currYear);
                document.dispatchEvent(new Event('activity-changed'));
                if (document.getElementById('cal-week-view')?.style.display === 'block') {
                    renderWeekView();
                }
            });
        });
        updateCalendarModeUi();
    }

    /* ── Initialise le comportement collapse ── */
    function initFilterCollapse() {
        const topbar = document.querySelector('.calendar-filters-topbar');
        const card   = document.querySelector('.calendar-filters-card');
        if (!topbar || !card) return;

        topbar.addEventListener('click', (e) => {
            // Ne pas fermer si on clique sur un bouton action
            if (e.target.closest('.filter-action-btn')) return;
            state.filtersCollapsed = card.classList.toggle('collapsed');
        });
    }

    function renderFilters(types, dossiers, statuts = [], priorites = [], responsables = []) {
        const filtersContainer = document.querySelector('.calendar-filters');

        if (!filtersContainer) {
            console.warn('Conteneur .calendar-filters non trouve');
            return;
        }

        const summaryText = buildFilterSummary();
        const totalTypes  = Object.keys(state.filtresTypes).length;
        const activeTypes = Object.values(state.filtresTypes).filter(Boolean).length;
        const totalDoss   = Object.keys(state.filtresDossiers).length;
        const activeDoss  = Object.values(state.filtresDossiers).filter(Boolean).length;
        const totalStatuts = Object.keys(state.filtresStatuts).length;
        const activeStatuts = Object.values(state.filtresStatuts).filter(Boolean).length;
        const totalPriorites = Object.keys(state.filtresPriorites).length;
        const activePriorites = Object.values(state.filtresPriorites).filter(Boolean).length;
        let badgeClass = 'filter-summary-badge';
        if (activeTypes === totalTypes && activeDoss === totalDoss
            && activeStatuts === totalStatuts && activePriorites === totalPriorites
            && !state.filtreClient && !state.filtreContact) badgeClass += ' all-active';
        else if (activeTypes === 0 && activeDoss === 0 && activeStatuts === 0 && activePriorites === 0) badgeClass += ' none-active';

        let typeOptions = '';
        types.forEach(type => {
            const typeKey = (type || 'autre').toLowerCase();
            const config  = TYPES_CONFIG[typeKey] || TYPES_CONFIG.autre;
            const count   = state.activites.filter(a => (a.type || '').toLowerCase() === typeKey).length;
            const sel     = state.filtresTypes[type] ? 'selected' : '';
            typeOptions += `<option value="${escapeHtml(type)}" ${sel}>${config.nom} (${count})</option>`;
        });

        let dossierOptions = '';
        dossiers.forEach((dossier, idx) => {
            const count = state.activites.filter(a => a.dossier === dossier).length;
            const sel   = state.filtresDossiers[dossier] ? 'selected' : '';
            const label = dossier || 'Sans dossier';
            dossierOptions += `<option value="${escapeHtml(dossier)}" ${sel}>${escapeHtml(label)} (${count})</option>`;
        });

        let statutOptions = '';
        statuts.forEach(statut => {
            const config = STATUTS_CONFIG[statut] || STATUTS_CONFIG.todo;
            const count = state.activites.filter(a => (a.statut || 'todo') === statut).length;
            const sel = state.filtresStatuts[statut] ? 'selected' : '';
            statutOptions += `<option value="${escapeHtml(statut)}" ${sel}>${config.nom} (${count})</option>`;
        });

        let prioriteOptions = '';
        priorites.forEach(priorite => {
            const config = PRIORITES_CONFIG[priorite] || PRIORITES_CONFIG.normal;
            const count = state.activites.filter(a => (a.priorite || 'normal') === priorite).length;
            const sel = state.filtresPriorites[priorite] ? 'selected' : '';
            prioriteOptions += `<option value="${escapeHtml(priorite)}" ${sel}>${config.nom} (${count})</option>`;
        });

        let responsableOptions = '';
        responsables.forEach(responsable => {
            const sample = state.activites.find(a => String(a.responsable_id || '') === String(responsable));
            const label = sample?.responsable_label || `Utilisateur ${responsable}`;
            const count = state.activites.filter(a => String(a.responsable_id || '') === String(responsable)).length;
            const sel = state.filtresResponsables[responsable] ? 'selected' : '';
            responsableOptions += `<option value="${escapeHtml(responsable)}" ${sel}>${escapeHtml(label)} (${count})</option>`;
        });

        const typesSize    = Math.min(Math.max(types.length, 2), 5);
        const dossiersSize = Math.min(Math.max(dossiers.length, 2), 6);
        const statutsSize  = Math.min(Math.max(statuts.length, 2), 4);
        const prioritesSize = Math.min(Math.max(priorites.length, 2), 4);
        const responsablesSize = Math.min(Math.max(responsables.length, 2), 5);

        const html = `
            <div class="calendar-filters-card${state.filtersCollapsed ? ' collapsed' : ''}">
                <div class="calendar-filters-topbar">
                    <div class="calendar-filters-title">
                        <i class="bi bi-funnel"></i>
                        <span>Filtres</span>
                        <span id="filter-summary-badge" class="${badgeClass}">${summaryText}</span>
                    </div>
                    <div class="calendar-filters-right">
                        <div class="calendar-filters-actions">
                            <button type="button" class="filter-action-btn" data-action="check-all">Tout</button>
                            <button type="button" class="filter-action-btn" data-action="uncheck-all">Aucun</button>
                        </div>
                        <i class="bi bi-chevron-down filter-chevron"></i>
                    </div>
                </div>

                <div class="calendar-filters-body">
                    <div class="calendar-filters-grid">

                        <div class="filter-panel">
                            <label class="filter-panel-title" for="filter-select-types">
                                <i class="bi bi-tags"></i>
                                <span>Types</span>
                            </label>
                            <div class="filter-select-wrapper">
                                <select id="filter-select-types" class="filter-select"
                                        multiple size="${typesSize}"
                                        data-filter-type="type">
                                    ${typeOptions}
                                </select>
                                <div class="filter-select-hint">Ctrl+clic pour multi-selection</div>
                            </div>
                        </div>

                        <div class="filter-panel">
                            <label class="filter-panel-title" for="filter-select-dossiers">
                                <i class="bi bi-folder2-open"></i>
                                <span>Dossiers</span>
                            </label>
                            <div class="filter-select-wrapper">
                                <select id="filter-select-dossiers" class="filter-select"
                                        multiple size="${dossiersSize}"
                                        data-filter-type="dossier">
                                    ${dossierOptions}
                                </select>
                                <div class="filter-select-hint">Ctrl+clic pour multi-selection</div>
                            </div>
                        </div>

                        <div class="filter-panel">
                            <label class="filter-panel-title" for="filter-select-statuts">
                                <i class="bi bi-check2-circle"></i>
                                <span>Statuts</span>
                            </label>
                            <div class="filter-select-wrapper">
                                <select id="filter-select-statuts" class="filter-select"
                                        multiple size="${statutsSize}"
                                        data-filter-type="statut">
                                    ${statutOptions}
                                </select>
                            </div>
                        </div>

                        <div class="filter-panel">
                            <label class="filter-panel-title" for="filter-select-priorites">
                                <i class="bi bi-exclamation-circle"></i>
                                <span>Priorités</span>
                            </label>
                            <div class="filter-select-wrapper">
                                <select id="filter-select-priorites" class="filter-select"
                                        multiple size="${prioritesSize}"
                                        data-filter-type="priorite">
                                    ${prioriteOptions}
                                </select>
                            </div>
                        </div>

                        <div class="filter-panel">
                            <label class="filter-panel-title" for="filter-select-responsables">
                                <i class="bi bi-person"></i>
                                <span>Responsables</span>
                            </label>
                            <div class="filter-select-wrapper">
                                <select id="filter-select-responsables" class="filter-select"
                                        multiple size="${responsablesSize}"
                                        data-filter-type="responsable">
                                    ${responsableOptions}
                                </select>
                                <div class="filter-select-hint">Activités sans responsable toujours visibles</div>
                            </div>
                        </div>

                        <div class="filter-panel">
                            <label class="filter-panel-title" for="filter-client">
                                <i class="bi bi-building"></i>
                                <span>Client</span>
                            </label>
                            <input id="filter-client" class="form-control" type="search"
                                   value="${escapeHtml(state.filtreClient)}" placeholder="Filtrer par client">
                        </div>

                        <div class="filter-panel">
                            <label class="filter-panel-title" for="filter-contact">
                                <i class="bi bi-person-lines-fill"></i>
                                <span>Contact</span>
                            </label>
                            <input id="filter-contact" class="form-control" type="search"
                                   value="${escapeHtml(state.filtreContact)}" placeholder="Filtrer par contact">
                        </div>

                    </div>
                </div>
            </div>
        `;

        filtersContainer.innerHTML = html;
        attachFilterEvents();
        attachFilterActionEvents();
        initFilterCollapse();
    }

    function attachFilterEvents() {
        const selects = document.querySelectorAll('.calendar-filters .filter-select');

        selects.forEach(select => {
            select.addEventListener('change', function () {
                const filterType = this.dataset.filterType;
                const options    = Array.from(this.options);

                options.forEach(opt => {
                    if (filterType === 'type') {
                        state.filtresTypes[opt.value] = opt.selected;
                    } else if (filterType === 'dossier') {
                        state.filtresDossiers[opt.value] = opt.selected;
                    } else if (filterType === 'statut') {
                        state.filtresStatuts[opt.value] = opt.selected;
                    } else if (filterType === 'priorite') {
                        state.filtresPriorites[opt.value] = opt.selected;
                    } else if (filterType === 'responsable') {
                        state.filtresResponsables[opt.value] = opt.selected;
                    }
                });

                updateFilterSummary();
                renderCalendar();
            });
        });

        const clientInput = document.getElementById('filter-client');
        const contactInput = document.getElementById('filter-contact');
        const bindSearch = (input, key) => {
            if (!input) return;
            input.addEventListener('input', function () {
                state[key] = this.value.trim().toLowerCase();
                updateFilterSummary();
                renderCalendar();
            });
        };
        bindSearch(clientInput, 'filtreClient');
        bindSearch(contactInput, 'filtreContact');
    }

    function attachFilterActionEvents() {
        const checkAllBtn   = document.querySelector('[data-action="check-all"]');
        const uncheckAllBtn = document.querySelector('[data-action="uncheck-all"]');

        if (checkAllBtn) {
            checkAllBtn.addEventListener('click', () => {
                Object.keys(state.filtresTypes).forEach(k => { state.filtresTypes[k] = true; });
                Object.keys(state.filtresDossiers).forEach(k => { state.filtresDossiers[k] = true; });
                Object.keys(state.filtresStatuts).forEach(k => { state.filtresStatuts[k] = true; });
                Object.keys(state.filtresPriorites).forEach(k => { state.filtresPriorites[k] = true; });
                Object.keys(state.filtresResponsables).forEach(k => { state.filtresResponsables[k] = true; });
                renderFilters(
                    Object.keys(state.filtresTypes),
                    Object.keys(state.filtresDossiers),
                    Object.keys(state.filtresStatuts),
                    Object.keys(state.filtresPriorites),
                    Object.keys(state.filtresResponsables)
                );
                renderCalendar();
            });
        }

        if (uncheckAllBtn) {
            uncheckAllBtn.addEventListener('click', () => {
                Object.keys(state.filtresTypes).forEach(k => { state.filtresTypes[k] = false; });
                Object.keys(state.filtresDossiers).forEach(k => { state.filtresDossiers[k] = false; });
                Object.keys(state.filtresStatuts).forEach(k => { state.filtresStatuts[k] = false; });
                Object.keys(state.filtresPriorites).forEach(k => { state.filtresPriorites[k] = false; });
                Object.keys(state.filtresResponsables).forEach(k => { state.filtresResponsables[k] = false; });
                renderFilters(
                    Object.keys(state.filtresTypes),
                    Object.keys(state.filtresDossiers),
                    Object.keys(state.filtresStatuts),
                    Object.keys(state.filtresPriorites),
                    Object.keys(state.filtresResponsables)
                );
                renderCalendar();
            });
        }
    }


    function getActivitiesForDate(dateStr) {
        return state.activites.filter(act => {
            if (act.date !== dateStr) return false;
            if (!state.filtresTypes[act.type]) return false;
            if (!state.filtresDossiers[act.dossier || '']) return false;
            if (!state.filtresStatuts[act.statut || 'todo']) return false;
            if (!state.filtresPriorites[act.priorite || 'normal']) return false;
            if (act.responsable_id && !state.filtresResponsables[act.responsable_id]) return false;
            return true;
        });
    }

    function hasActivities(dateStr) {
        return getActivitiesForDate(dateStr).length > 0;
    }


    function renderCalendar() {
        console.log(' Rendu du calendrier');

        let firstDayOfMonth     = new Date(state.currYear, state.currMonth, 0).getDay();
        let lastDateOfMonth     = new Date(state.currYear, state.currMonth + 1, 0).getDate();
        let lastDayOfMonth      = new Date(state.currYear, state.currMonth, lastDateOfMonth).getDay();
        let lastDateOfLastMonth = new Date(state.currYear, state.currMonth, 0).getDate();

        days.innerHTML = "";
        let weekCounter = 0;
        let ul = document.createElement("ul");

        for (let i = firstDayOfMonth; i > 0; --i) {
            let li = createDayElement(lastDateOfLastMonth - i + 1, true, -1);
            ul.append(li);
            ++weekCounter;
            if (weekCounter === 7) { days.append(ul); ul = document.createElement("ul"); weekCounter = 0; }
        }

        for (let i = 1; i <= lastDateOfMonth; ++i) {
            let li = createDayElement(i, false, 0);
            ul.append(li);
            ++weekCounter;
            if (weekCounter === 7) { days.append(ul); ul = document.createElement("ul"); weekCounter = 0; }
        }

        for (let i = lastDayOfMonth; i < 7; ++i) {
            let li = createDayElement(i - lastDayOfMonth + 1, true, 1);
            ul.append(li);
            ++weekCounter;
            if (weekCounter === 7) { days.append(ul); ul = document.createElement("ul"); weekCounter = 0; }
        }

        if (weekCounter > 0) {
            for (let i = 0; i < 7 - weekCounter; ++i) { ul.append(document.createElement("li")); }
            days.append(ul);
        }

        currentDate.innerText = `${MOIS[state.currMonth]} ${state.currYear}`;
        updateCalendarExportLink();
    }

    function createDayElement(day, isInactive, monthOffset) {
        let li = document.createElement("li");
        li.innerText = day;

        if (isInactive) {
            li.classList.add("inactive");
            li.addEventListener("click", () => { changeMonth(state.currMonth + monthOffset); });
        } else {
            const dateStr = `${state.currYear}-${String(state.currMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

            if (day === state.date.getDate() &&
                state.currMonth === new Date().getMonth() &&
                state.currYear  === new Date().getFullYear()) {
                li.classList.add("current");
            }

            if (hasActivities(dateStr)) {
                li.classList.add("has-activity");
                const dayActs = getActivitiesForDate(dateStr);
                if (dayActs.some(act => act.is_overdue)) {
                    li.style.boxShadow = 'inset 0 0 0 2px #dc2626';
                } else if (dayActs.some(act => ['high', 'urgent'].includes(act.priorite))) {
                    li.style.boxShadow = 'inset 0 0 0 2px #f97316';
                }

                li.addEventListener("mouseenter", (e) => { showTooltip(dateStr, e); });
                li.addEventListener("mousemove",  (e) => { positionTooltip(e); });
                li.addEventListener("mouseleave", ()  => { hideTooltip(); });
            }

            li.addEventListener("click", () => {
                li.classList.add("active");
                document.querySelectorAll(".calendar .active").forEach(el => {
                    if (el !== li) el.classList.remove("active");
                });

                if (hasActivities(dateStr)) {
                    const activites = getActivitiesForDate(dateStr);
                    if (activites.length === 1) {
                        openModalWithActivity(activites[0], dateStr);
                    } else if (activites.length > 1) {
                        openActivityPickerModal(activites, dateStr);
                    }
                }
            });
        }

        return li;
    }

    function openModalWithActivity(act, dateStr) {
        if (state.calendarReadOnly) {
            alert("Le calendrier administrateur est disponible en lecture seule.");
            return;
        }
        const modal = document.getElementById('activity-modal');
        if (!modal) return;

        const titleEl = document.getElementById('activity-modal-title');
        if (titleEl) {
            titleEl.innerHTML = '<i class="bi bi-calendar-check"></i> Modifier / Supprimer une activité';
        }

        const dossierSelect    = document.getElementById('activity-dossier');
        const societeSelect    = document.getElementById('activity-societe');
        const titleInput       = document.getElementById('activity-title');
        const typeSelect       = document.getElementById('activity-type');
        const dateInput        = document.getElementById('activity-date');
        const dureeSelect      = document.getElementById('activity-duree-minutes');
        const responsableSelect = document.getElementById('activity-responsable');
        const statutSelect     = document.getElementById('activity-statut');
        const prioriteSelect   = document.getElementById('activity-priorite');
        const clientInput      = document.getElementById('activity-client');
        const contactInput     = document.getElementById('activity-contact-externe');
        const syncInput        = document.getElementById('activity-sync-outlook');
        const commentInput     = document.getElementById('activity-commentaire');
        const deleteBtn        = document.getElementById('delete-activity-btn');
        const dossierNomDisplay = document.getElementById('dossier-nom-display');

        const timeStr = act.time || (act.datetime ? act.datetime.slice(11, 16) : '00:00');
        const fullDateStr = `${dateStr}T${timeStr}`;

        if (dossierSelect) {
            dossierSelect.value = act.dossier || '';
            const selectedOption = dossierSelect.options[dossierSelect.selectedIndex];
            const dossierNom     = act.dossier_nom || selectedOption?.dataset?.nom || act.dossier || '';
            if (dossierNomDisplay) {
                dossierNomDisplay.style.display = dossierNom ? 'block' : 'none';
            }
        }
        if (titleInput) titleInput.value = act.titre || '';
        if (societeSelect) societeSelect.value = act.societe_id || '';
        if (typeSelect)    typeSelect.value    = act.type       || '';
        if (dateInput)     dateInput.value     = fullDateStr;
        if (dureeSelect)   dureeSelect.value   = String(act.duree_minutes || 60);
        if (responsableSelect) responsableSelect.value = act.responsable_id || '';
        if (statutSelect) statutSelect.value = act.statut || 'todo';
        if (prioriteSelect) prioriteSelect.value = act.priorite || 'normal';
        if (syncInput) syncInput.checked = !!act.outlook_synced;
        if (commentInput)  commentInput.value  = act.commentaire || '';

        if (deleteBtn) {
            deleteBtn.style.display = 'inline-flex';
            deleteBtn.dataset.activityId = act.id || '';
        }

        const form = document.getElementById('activity-form');
        if (form) {
            form.dataset.mode         = 'edit';
            form.dataset.activityId   = act.id   || '';
            form.dataset.originalDate = dateStr  || '';
        }

        modal.style.display = 'flex';
    }

    window.openModalWithActivity = openModalWithActivity;

    function openActivityPickerModal(activites, dateStr) {
        let picker = document.getElementById('activity-picker-modal');
        if (!picker) {
            picker = document.createElement('div');
            picker.id = 'activity-picker-modal';
            picker.style.cssText = `
                display:none; position:fixed; inset:0; background:rgba(0,0,0,0.5);
                z-index:9999; align-items:center; justify-content:center;
            `;
            picker.innerHTML = `
                <div style="background:#fff;border-radius:12px;padding:1.5rem;
                            max-width:420px;width:90%;box-shadow:0 10px 40px rgba(0,0,0,0.2);">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
                        <h3 style="margin:0;color:#1e3c72;font-size:1.1rem;">
                            <i class="bi bi-list-ul"></i> Choisir une activité
                        </h3>
                        <button onclick="document.getElementById('activity-picker-modal').style.display='none'"
                                style="border:none;background:none;font-size:1.5rem;cursor:pointer;color:#888;">&times;</button>
                    </div>
                    <div id="activity-picker-list" style="display:flex;flex-direction:column;gap:.5rem;"></div>
                </div>`;
            document.body.appendChild(picker);
        }

        const list = document.getElementById('activity-picker-list');
        list.innerHTML = '';

        activites.forEach(act => {
            const typeKey    = (act.type || 'autre').toLowerCase();
            const config     = TYPES_CONFIG[typeKey] || TYPES_CONFIG['autre'];
            const nomDossier = act.dossier_nom || act.dossier;
            const title = act.titre || config.nom;
            const borderColor = act.is_overdue ? '#dc2626' : (act.priority_color || config.couleur);

            const btn = document.createElement('button');
            btn.style.cssText = `
                border:1px solid #e0e0e0; border-left:4px solid ${borderColor};
                background:#fff; border-radius:8px; padding:.65rem .9rem;
                cursor:pointer; text-align:left; font-size:.88rem; transition:.15s;
            `;
            btn.innerHTML = `
                <strong style="color:${borderColor};">${escapeHtml(title)}</strong>
                <span style="display:block;font-weight:600;color:#222;margin-top:2px;">
                    📁 ${escapeHtml(nomDossier)}
                </span>
                <small style="color:#64748b;">${escapeHtml(act.statut_label || '')} · ${escapeHtml(act.priorite_label || '')}</small>
                ${act.dossier_nom && act.dossier_nom !== act.dossier
                    ? `<span style="display:block;font-size:.75rem;color:#888;">${escapeHtml(act.dossier)}</span>`
                    : ''}
                ${act.commentaire
                    ? `<small style="display:block;color:#888;">${escapeHtml(act.commentaire)}</small>`
                    : ''}`;
            btn.addEventListener('mouseenter', () => btn.style.borderColor = borderColor);
            btn.addEventListener('mouseleave', () => btn.style.borderColor = '#e0e0e0');
            btn.addEventListener('click', () => {
                picker.style.display = 'none';
                openModalWithActivity(act, dateStr);
            });
            list.appendChild(btn);
        });

        picker.style.display = 'flex';
    }

    function changeMonth(newMonth) {
        if (newMonth < 0 || newMonth > 11) {
            state.date     = new Date(state.currYear, newMonth, new Date().getDate());
            state.currYear = state.date.getFullYear();
            state.currMonth = state.date.getMonth();
        } else {
            state.date = new Date();
        }

        hideTooltip();
        loadActivities(state.currMonth, state.currYear);
    }


    console.log(' Initialisation du calendrier avec tooltips');

    createTooltip();
    setupCalendarScopeButtons();
    loadActivities(state.currMonth, state.currYear);

    prevNextIcon.forEach(icon => {
        icon.addEventListener("click", () => {
            state.currMonth = (icon.id === "prev" ? (state.currMonth - 1) : (state.currMonth + 1));
            changeMonth(state.currMonth);
        });
    });

    window.addEventListener('scroll', hideTooltip);

})();



(function() {
    console.log(' Script modal activité chargé');

    const modal     = document.getElementById('activity-modal');
    const openBtn   = document.getElementById('add-activity-btn');
    const closeBtn  = document.getElementById('close-modal-btn');
    const cancelBtn = document.getElementById('cancel-activity-btn');
    const deleteBtn = document.getElementById('delete-activity-btn');
    const form      = document.getElementById('activity-form');
    const statusDiv = document.getElementById('activity-form-status');
    const dossierSelect = document.getElementById('activity-dossier');
    const societeSelect = document.getElementById('activity-societe');

    dossierSelect?.addEventListener('change', function() {
        const option = this.options[this.selectedIndex];
        if (societeSelect) societeSelect.value = option?.dataset?.societe || '';
    });

    console.log('Modal:', modal);
    console.log('Button:', openBtn);
    console.log('Delete Button:', deleteBtn);
    console.log('Form:', form);

    if (!modal || !openBtn || !form || !deleteBtn) {
        console.warn('Éléments du modal activité non trouvés');
        console.log('modal présent:', !!modal);
        console.log('openBtn présent:', !!openBtn);
        console.log('deleteBtn présent:', !!deleteBtn);
        console.log('form présent:', !!form);
        return;
    }

    console.log('Tous les éléments trouvés, attachement des événements...');


    openBtn.addEventListener('click', function() {
        if (window.adminCalendarState?.calendarReadOnly) return;
        console.log('Clic sur le bouton détecté !');
        const modalTitle = modal.querySelector('.activity-modal-header h3');
        if (modalTitle) modalTitle.innerHTML = '<i class="bi bi-calendar-plus"></i> Nouvelle activité';
        form.reset();
        form.dataset.mode = 'create';
        form.dataset.activityId = '';
        deleteBtn.style.display = 'none';
        document.getElementById('activity-statut').value = 'todo';
        document.getElementById('activity-priorite').value = 'normal';
        document.getElementById('activity-duree-minutes').value = '60';
        modal.style.display = 'flex';
        const now = new Date();
        document.getElementById('activity-date').value = now.toISOString().slice(0, 16);
    });

    function closeModal() {
        modal.style.display = 'none';
        form.reset();
        form.dataset.mode = 'create';
        form.dataset.activityId = '';
        deleteBtn.style.display = 'none';
        statusDiv.style.display = 'none';
    }

    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);

    modal.addEventListener('click', function(e) {
        if (e.target === modal) { closeModal(); }
    });

    deleteBtn.addEventListener('click', function() {
        const formData = {
            activity_id: deleteBtn.dataset.activityId || form.dataset.activityId || '',
            dossier:     document.getElementById('activity-dossier').value.trim(),
            societe:     document.getElementById('activity-societe').value,
            type:        document.getElementById('activity-type').value,
            date:        document.getElementById('activity-date').value,
            commentaire: document.getElementById('activity-commentaire').value.trim()
        };

        if (!formData.type || !formData.date) {
            showStatus('Veuillez remplir tous les champs obligatoires pour supprimer', 'error');
            return;
        }

        const dossierLabel = formData.dossier || 'Sans dossier';
        if (!confirm(`Êtes-vous sûr de vouloir supprimer l'activité correspondant à ces critères ?\n\nDossier: ${dossierLabel}\nType: ${formData.type}\nDate: ${formData.date}`)) {
            return;
        }

        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Suppression...';

        const csrftoken = getCookie('csrftoken');

        fetch('/api/delete-activity/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            deleteBtn.disabled = false;
            deleteBtn.innerHTML = '<i class="bi bi-trash"></i> Supprimer';

            if (data.success) {
                const warning = data.warning ? ` Attention : ${data.warning}` : '';
                showStatus(`${data.deleted_count} activité(s) supprimée(s) avec succès !${warning}`, 'success');
                document.dispatchEvent(new Event('activity-changed'));
                setTimeout(() => { closeModal(); location.reload(); }, 800);
            } else {
                showStatus(data.message || 'Erreur lors de la suppression', 'error');
            }
        })
        .catch(error => {
            deleteBtn.disabled = false;
            deleteBtn.innerHTML = '<i class="bi bi-trash"></i> Supprimer';
            showStatus(' Erreur réseau : ' + error, 'error');
            console.error('Erreur:', error);
        });
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = {
            titre:       document.getElementById('activity-title').value.trim(),
            dossier:     document.getElementById('activity-dossier').value.trim(),
            societe:     document.getElementById('activity-societe').value,
            type:        document.getElementById('activity-type').value,
            date:        document.getElementById('activity-date').value,
            duree_minutes: document.getElementById('activity-duree-minutes').value,
            responsable: document.getElementById('activity-responsable').value,
            statut:      document.getElementById('activity-statut').value,
            priorite:    document.getElementById('activity-priorite').value,
            commentaire: document.getElementById('activity-commentaire').value.trim(),
            sync_outlook: document.getElementById('activity-sync-outlook')?.checked || false
        };

        if (!formData.type || !formData.date) {
            showStatus('Veuillez remplir tous les champs obligatoires', 'error');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Enregistrement...';

        const csrftoken = getCookie('csrftoken');

        const isEdit = form.dataset.mode === 'edit' && form.dataset.activityId;
        const url = isEdit
            ? `/api/update-activity/${encodeURIComponent(form.dataset.activityId)}/`
            : '/api/create-activity/';

        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-check-circle"></i> Enregistrer';

            if (data.success) {
                const warning = data.warning ? ` Attention : ${data.warning}` : '';
                showStatus(` Activité ${isEdit ? 'mise à jour' : 'créée'} avec succès !${warning}`, 'success');
                document.dispatchEvent(new Event('activity-changed'));
                setTimeout(() => { closeModal(); location.reload(); }, 800);
            } else {
                showStatus(' ' + (data.message || 'Erreur lors de la création'), 'error');
            }
        })
        .catch(error => {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-check-circle"></i> Enregistrer';
            showStatus(' Erreur réseau : ' + error, 'error');
            console.error('Erreur:', error);
        });
    });

    function showStatus(message, type) {
        statusDiv.textContent = message;
        statusDiv.className   = type;
        statusDiv.style.display = 'block';
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    console.log(' Événements attachés avec succès');
})();


/* ============================================================
   VUE SEMAINE — AGENDA HEURE PAR HEURE
   ============================================================ */
(function () {
    function escapeHtml(value) {
        return String(value || '').replace(/[&<>"']/g, char => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[char]));
    }

    /* ── constantes ── */
    const HOUR_PX    = 56;
    const DAY_START  = 0;
    const DAY_END    = 24;
    const JOURS      = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
    const MOIS_COURT = ['jan', 'fév', 'mar', 'avr', 'mai', 'jun',
                        'jul', 'aoû', 'sep', 'oct', 'nov', 'déc'];

    const COLORS = {
        'vente':     '#27ae60',
        'location':  '#3498db',
        'compromis': '#e74c3c',
        'visite':    '#f39c12',
        'relance':   '#9b59b6',
        'autre':     '#95a5a6',
    };

    /* ── état ── */
    let weekRefDate   = new Date();
    let weekActivites = [];
    let nowLineTimer  = null;

    /* ── utilitaires date ── */
    function getMonday(d) {
        const dt  = new Date(d);
        const day = dt.getDay();
        const diff = (day === 0) ? -6 : 1 - day;
        dt.setDate(dt.getDate() + diff);
        dt.setHours(0, 0, 0, 0);
        return dt;
    }

    function addDays(d, n) {
        const dt = new Date(d);
        dt.setDate(dt.getDate() + n);
        return dt;
    }

    function isSameDay(a, b) {
        return a.getFullYear() === b.getFullYear() &&
               a.getMonth()    === b.getMonth()    &&
               a.getDate()     === b.getDate();
    }

    function toISODate(d) {
        return d.toISOString().split('T')[0];
    }

    function formatWeekTitle(monday) {
        const sunday  = addDays(monday, 6);
        const fmtDay  = d => `${d.getDate()} ${MOIS_COURT[d.getMonth()]}`;
        const yearPart = monday.getFullYear() !== sunday.getFullYear()
            ? ` ${monday.getFullYear()}` : '';
        return `Semaine du ${fmtDay(monday)}${yearPart} au ${fmtDay(sunday)} ${sunday.getFullYear()}`;
    }

    /* ── rendu de la colonne des heures ── */
    function renderTimeCol() {
        const col = document.getElementById('agenda-time-col');
        if (!col) return;
        col.innerHTML = '';
        for (let h = DAY_START; h < DAY_END; h++) {
            const lbl = document.createElement('div');
            lbl.className   = 'agenda-hour-label';
            lbl.textContent = h === 0 ? '' : `${String(h).padStart(2, '0')}h`;
            col.appendChild(lbl);
        }
    }

    /* ── rendu des headers de jours ── */
    function renderDayHeaders(monday) {
        const container = document.getElementById('agenda-header-days');
        if (!container) return;
        container.innerHTML = '';
        const today = new Date();
        for (let i = 0; i < 7; i++) {
            const dayDate  = addDays(monday, i);
            const isToday  = isSameDay(dayDate, today);
            const isWeekend = i >= 5;
            const hdr = document.createElement('div');
            hdr.className = 'agenda-day-header'
                + (isToday   ? ' today'   : '')
                + (isWeekend ? ' weekend' : '');
            hdr.innerHTML = `
                <span class="day-name">${JOURS[i]}</span>
                <span class="day-num">${dayDate.getDate()}</span>
            `;
            container.appendChild(hdr);
        }
    }

    /* ── rendu de la grille des 7 jours ── */
    function renderDaysCols(monday, activites) {
        const container = document.getElementById('agenda-days-cols');
        if (!container) return;
        container.innerHTML = '';

        const today = new Date();

        for (let i = 0; i < 7; i++) {
            const dayDate  = addDays(monday, i);
            const isToday  = isSameDay(dayDate, today);
            const isWeekend = i >= 5;

            const col = document.createElement('div');
            col.className = 'agenda-day-col' + (isWeekend ? ' weekend' : '');

            const cellsWrapper = document.createElement('div');
            cellsWrapper.style.position = 'relative';
            cellsWrapper.style.height   = `${(DAY_END - DAY_START) * HOUR_PX}px`;

            for (let h = DAY_START; h < DAY_END; h++) {
                const cell = document.createElement('div');
                cell.className = 'agenda-cell half-hour';
                cellsWrapper.appendChild(cell);
            }

            if (isToday) {
                const now   = new Date();
                const mins  = (now.getHours() - DAY_START) * 60 + now.getMinutes();
                const topPx = (mins / 60) * HOUR_PX;
                const line  = document.createElement('div');
                line.className = 'agenda-now-line';
                line.id        = 'now-line-' + i;
                line.style.top = `${topPx}px`;
                cellsWrapper.appendChild(line);
            }

            const dayActivites = activites.filter(act => {
                if (!act.datetime) return false;
                return isSameDay(new Date(act.datetime), dayDate);
            });

            dayActivites.forEach(act => {
                const el = buildEventBlock_week(act);
                if (el) cellsWrapper.appendChild(el);
            });

            col.appendChild(cellsWrapper);
            container.appendChild(col);
        }
    }

    function buildEventBlock_week(act) {
        if (!act.datetime) return null;
        const dt  = new Date(act.datetime);
        const h   = dt.getHours();
        const m   = dt.getMinutes();

        const topPx    = ((h - DAY_START) * 60 + m) / 60 * HOUR_PX;
        const durationMinutes = Number(act.duree_minutes || 60);
        const heightPx = Math.max(22, (durationMinutes / 60) * HOUR_PX);

        const typeKey    = (act.type || 'autre').toLowerCase();
        const color      = act.is_overdue ? '#dc2626' : (act.priority_color || COLORS[typeKey] || COLORS['autre']);
        const label      = act.titre || (act.type ? (act.type.charAt(0).toUpperCase() + act.type.slice(1)) : 'Activité');
        const timeStr    = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
        const nomDossier = act.dossier_nom || act.dossier;

        const el = document.createElement('div');
        el.className   = 'agenda-event';
        el.style.cssText = `top:${topPx}px;height:${heightPx}px;background:${color};`;
        el.innerHTML = `
            <span class="ev-time">${timeStr}${act.end_time ? `-${escapeHtml(act.end_time)}` : ''}</span>
            <span class="ev-title">${escapeHtml(label)} — ${escapeHtml(nomDossier)}</span>`;

        el.addEventListener('click', () => {
            if (typeof openModalWithActivity === 'function') {
                openModalWithActivity(act, act.date);
            }
        });
        return el;
    }

    /* ── mise à jour du trait "maintenant" toutes les minutes ── */
    function startNowLineUpdater() {
        if (nowLineTimer) clearInterval(nowLineTimer);
        nowLineTimer = setInterval(() => {
            const now   = new Date();
            const mins  = (now.getHours() - DAY_START) * 60 + now.getMinutes();
            const topPx = (mins / 60) * HOUR_PX;
            for (let i = 0; i < 7; i++) {
                const line = document.getElementById('now-line-' + i);
                if (line) line.style.top = `${topPx}px`;
            }
        }, 60_000);
    }

    /* ── scroll auto vers l'heure courante ── */
    function scrollToNow() {
        const wrapper = document.querySelector('.agenda-grid-wrapper');
        if (!wrapper) return;
        const now   = new Date();
        const mins  = (now.getHours() - DAY_START) * 60 + now.getMinutes();
        const topPx = (mins / 60) * HOUR_PX;
        wrapper.scrollTop = Math.max(0, topPx - HOUR_PX * 2);
    }

    /* ── chargement des activités via l'API ── */
    async function loadWeekActivities(refDate) {
        const loading = document.getElementById('week-loading');
        if (loading) loading.style.display = 'block';
        try {
            const dateStr = toISODate(refDate);
            const calendarState = window.adminCalendarState || { calendarScope: 'mine', calendarReadOnly: false };
            const params = new URLSearchParams({
                date: dateStr,
                calendar_scope: calendarState.calendarScope
            });
            const resp = await fetch(`/api/calendar-activities-week/?${params.toString()}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            weekActivites = data.success ? data.activites : [];
            calendarState.calendarReadOnly = !!data.read_only;
            window.updateCalendarModeUi?.();
        } catch (e) {
            console.error('Erreur chargement semaine:', e);
            weekActivites = [];
        } finally {
            if (loading) loading.style.display = 'none';
        }
    }

    /* ── rendu complet de la vue semaine ── */
    async function renderWeekView() {
        const monday = getMonday(weekRefDate);

        const title = document.getElementById('week-title');
        if (title) title.textContent = formatWeekTitle(monday);

        await loadWeekActivities(weekRefDate);
        renderTimeCol();
        renderDayHeaders(monday);
        renderDaysCols(monday, weekActivites);
        scrollToNow();
        startNowLineUpdater();
    }

    /* ── switch vue exposé globalement ── */
    window.calSwitchView = function (view) {
        const monthView = document.getElementById('cal-month-view');
        const weekView  = document.getElementById('cal-week-view');
        const btnMonth  = document.getElementById('btn-view-month');
        const btnWeek   = document.getElementById('btn-view-week');

        if (view === 'week') {
            if (monthView) monthView.style.display = 'none';
            if (weekView)  weekView.style.display  = 'block';
            if (btnMonth)  btnMonth.classList.remove('active');
            if (btnWeek)   btnWeek.classList.add('active');
            renderWeekView();
        } else {
            if (monthView) monthView.style.display = 'block';
            if (weekView)  weekView.style.display  = 'none';
            if (btnMonth)  btnMonth.classList.add('active');
            if (btnWeek)   btnWeek.classList.remove('active');
            if (nowLineTimer) { clearInterval(nowLineTimer); nowLineTimer = null; }
        }
    };

    /* ── boutons navigation semaine ── */
    document.addEventListener('DOMContentLoaded', () => {
        const prevBtn  = document.getElementById('week-prev');
        const nextBtn  = document.getElementById('week-next');
        const todayBtn = document.getElementById('week-today');

        if (prevBtn)  prevBtn.addEventListener('click',  () => { weekRefDate = addDays(weekRefDate, -7); renderWeekView(); });
        if (nextBtn)  nextBtn.addEventListener('click',  () => { weekRefDate = addDays(weekRefDate,  7); renderWeekView(); });
        if (todayBtn) todayBtn.addEventListener('click', () => { weekRefDate = new Date();               renderWeekView(); });
    });

    console.log('✅ Vue semaine agenda chargée');

})();
