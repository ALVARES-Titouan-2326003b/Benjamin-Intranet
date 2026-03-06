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

    const MOIS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"];



    let state = {
        date: new Date(),
        currYear: new Date().getFullYear(),
        currMonth: new Date().getMonth(),
        activites: [],
        filtresTypes: {},
        filtresDossiers: {}
    };

    // Éléments DOM
    const days = document.querySelector(".days");
    const currentDate = document.querySelector(".current-date");
    const prevNextIcon = document.querySelectorAll(".icons span");

    // Tooltip
    let tooltipElement = null;



    function createTooltip() {
        if (tooltipElement) return;

        tooltipElement = document.createElement('div');
        tooltipElement.className = 'activity-tooltip';
        document.body.appendChild(tooltipElement);
    }

    function showTooltip(dateStr, mouseEvent) {
        if (!tooltipElement) createTooltip();

        const activites = getActivitiesForDate(dateStr);

        if (activites.length === 0) {
            hideTooltip();
            return;
        }

        let html = `<div class="activity-tooltip-header">`;
        html += ` ${formatDateForDisplay(dateStr)} - ${activites.length} activité${activites.length > 1 ? 's' : ''}`;
        html += `</div>`;

        activites.forEach(act => {
            const config = TYPES_CONFIG[act.type] || TYPES_CONFIG['autre'];

            html += `<div class="activity-tooltip-item" data-type="${act.type}">`;
            html += `<div class="activity-tooltip-type">`;
            html += `<span class="activity-tooltip-color" style="background: ${config.couleur}"></span>`;
            html += `<span class="activity-tooltip-type-label">${config.nom}</span>`;
            html += `</div>`;
            html += `<div class="activity-tooltip-dossier">📁 ${act.dossier}</div>`;

            if (act.description) {
                html += `<div class="activity-tooltip-description">${act.description}</div>`;
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
        let top = mouseEvent.clientY + padding;

        if (left + tooltipRect.width > window.innerWidth) {
            left = mouseEvent.clientX - tooltipRect.width - padding;
        }

        if (top + tooltipRect.height > window.innerHeight) {
            top = mouseEvent.clientY - tooltipRect.height - padding;
        }

        left = Math.max(padding, left);
        top = Math.max(padding, top);

        tooltipElement.style.left = `${left}px`;
        tooltipElement.style.top = `${top}px`;
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

            const response = await fetch(
                `/api/calendar-activities/?month=${month + 1}&year=${year}`
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                state.activites = data.activites;
                console.log(` ${data.activites.length} activités chargées`);

                initFilters();
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
        const typesUniques = [...new Set(state.activites.map(a => a.type))];
        const dossiersUniques = [...new Set(state.activites.map(a => a.dossier))];

        state.filtresTypes = {};
        typesUniques.forEach(type => {
            state.filtresTypes[type] = true;
        });

        state.filtresDossiers = {};
        dossiersUniques.forEach(dossier => {
            state.filtresDossiers[dossier] = true;
        });

        renderFilters(typesUniques, dossiersUniques);
    }

    function renderFilters(types, dossiers) {
        let filtersContainer = document.querySelector('.calendar-filters');

        if (!filtersContainer) {
            console.warn('  Conteneur .calendar-filters non trouvé');
            return;
        }

        let filtersHTML = '<div class="filters-content">';

        filtersHTML += '<div class="filter-group">';
        filtersHTML += '<h4>Types d\'activités :</h4>';
        filtersHTML += '<div class="filter-checkboxes">';

        types.forEach(type => {
            const config = TYPES_CONFIG[type] || TYPES_CONFIG['autre'];
            const count = state.activites.filter(a => a.type === type).length;

            filtersHTML += `
                <label class="filter-checkbox">
                    <input type="checkbox" 
                           data-filter-type="type" 
                           data-value="${type}" 
                           ${state.filtresTypes[type] ? 'checked' : ''}>
                    <span class="filter-color" style="background: ${config.couleur}"></span>
                    <span class="filter-label">${config.nom} (${count})</span>
                </label>
            `;
        });

        filtersHTML += '</div></div>';

        filtersHTML += '<div class="filter-group">';
        filtersHTML += '<h4>Dossiers :</h4>';
        filtersHTML += '<div class="filter-checkboxes">';

        dossiers.forEach(dossier => {
            const count = state.activites.filter(a => a.dossier === dossier).length;

            filtersHTML += `
                <label class="filter-checkbox">
                    <input type="checkbox" 
                           data-filter-type="dossier" 
                           data-value="${dossier}" 
                           ${state.filtresDossiers[dossier] ? 'checked' : ''}>
                    <span class="filter-label">${dossier} (${count})</span>
                </label>
            `;
        });

        filtersHTML += '</div></div>';
        filtersHTML += '</div>';

        filtersContainer.innerHTML = filtersHTML;
        attachFilterEvents();
    }

    function attachFilterEvents() {
        const checkboxes = document.querySelectorAll('.calendar-filters input[type="checkbox"]');

        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const filterType = this.dataset.filterType;
                const value = this.dataset.value;
                const isChecked = this.checked;

                if (filterType === 'type') {
                    state.filtresTypes[value] = isChecked;
                } else if (filterType === 'dossier') {
                    state.filtresDossiers[value] = isChecked;
                }

                renderCalendar();
            });
        });
    }



    function getActivitiesForDate(dateStr) {
        return state.activites.filter(act => {
            if (act.date !== dateStr) return false;
            if (!state.filtresTypes[act.type]) return false;
            if (!state.filtresDossiers[act.dossier]) return false;
            return true;
        });
    }

    function hasActivities(dateStr) {
        return getActivitiesForDate(dateStr).length > 0;
    }



    function renderCalendar() {
        console.log(' Rendu du calendrier');

        let firstDayOfMonth = new Date(state.currYear, state.currMonth, 0).getDay();
        let lastDateOfMonth = new Date(state.currYear, state.currMonth + 1, 0).getDate();
        let lastDayOfMonth = new Date(state.currYear, state.currMonth, lastDateOfMonth).getDay();
        let lastDateOfLastMonth = new Date(state.currYear, state.currMonth, 0).getDate();

        days.innerHTML = "";
        let weekCounter = 0;
        let ul = document.createElement("ul");

        for (let i = firstDayOfMonth; i > 0; --i) {
            let li = createDayElement(lastDateOfLastMonth - i + 1, true, -1);
            ul.append(li);
            ++weekCounter;
            if (weekCounter === 7) {
                days.append(ul);
                ul = document.createElement("ul");
                weekCounter = 0;
            }
        }

        for (let i = 1; i <= lastDateOfMonth; ++i) {
            let li = createDayElement(i, false, 0);
            ul.append(li);
            ++weekCounter;
            if (weekCounter === 7) {
                days.append(ul);
                ul = document.createElement("ul");
                weekCounter = 0;
            }
        }

        for (let i = lastDayOfMonth; i < 7; ++i) {
            let li = createDayElement(i - lastDayOfMonth + 1, true, 1);
            ul.append(li);
            ++weekCounter;
            if (weekCounter === 7) {
                days.append(ul);
                ul = document.createElement("ul");
                weekCounter = 0;
            }
        }

        if (weekCounter > 0) {
            for (let i = 0; i < 7 - weekCounter; ++i) {
                ul.append(document.createElement("li"));
            }
            days.append(ul);
        }

        currentDate.innerText = `${MOIS[state.currMonth]} ${state.currYear}`;
    }

    function createDayElement(day, isInactive, monthOffset) {
        let li = document.createElement("li");
        li.innerText = day;

        if (isInactive) {
            li.classList.add("inactive");
            li.addEventListener("click", () => {
                changeMonth(state.currMonth + monthOffset);
            });
        } else {
            const dateStr = `${state.currYear}-${String(state.currMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

            if (day === state.date.getDate() &&
                state.currMonth === new Date().getMonth() &&
                state.currYear === new Date().getFullYear()) {
                li.classList.add("current");
            }

            if (hasActivities(dateStr)) {
                li.classList.add("has-activity");

                li.addEventListener("mouseenter", (e) => {
                    showTooltip(dateStr, e);
                });

                li.addEventListener("mousemove", (e) => {
                    positionTooltip(e);
                });

                li.addEventListener("mouseleave", () => {
                    hideTooltip();
                });
            }

            li.addEventListener("click", () => {
                li.classList.add("active");
                let currentActive = document.querySelectorAll(".active");
                currentActive.forEach((activeEle) => {
                    if (activeEle !== li) activeEle.classList.remove("active");
                });

                // Si le jour a des activités, ouvrir le modal pré-rempli
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
        const modal = document.getElementById('activity-modal');
        if (!modal) return;

        // Changer le titre du modal
        const modalTitle = modal.querySelector('.activity-modal-header h3');
        if (modalTitle) modalTitle.innerHTML = '<i class="bi bi-calendar-check"></i> Modifier / Supprimer une activité';

        // Pré-remplir le formulaire
        const dossierSelect = document.getElementById('activity-dossier');
        const typeSelect = document.getElementById('activity-type');
        const dateInput = document.getElementById('activity-date');
        const commentaireInput = document.getElementById('activity-commentaire');

        if (dossierSelect) dossierSelect.value = act.dossier;
        if (typeSelect) typeSelect.value = act.type;
        if (dateInput) dateInput.value = `${dateStr}T00:00`;
        if (commentaireInput) commentaireInput.value = act.commentaire || '';

        modal.style.display = 'flex';
    }



    function openActivityPickerModal(activites, dateStr) {
        // Créer ou récupérer le picker
        let picker = document.getElementById('activity-picker-modal');
        if (!picker) {
            picker = document.createElement('div');
            picker.id = 'activity-picker-modal';
            picker.style.cssText = `
                display:none; position:fixed; inset:0; background:rgba(0,0,0,0.5);
                z-index:9999; align-items:center; justify-content:center;
            `;
            picker.innerHTML = `
                <div style="background:#fff; border-radius:12px; padding:1.5rem; max-width:420px; width:90%; box-shadow:0 10px 40px rgba(0,0,0,0.2);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                        <h3 style="margin:0; color:#1e3c72; font-size:1.1rem;">
                            <i class="bi bi-list-ul"></i> Choisir une activité
                        </h3>
                        <button id="picker-close-btn" style="background:none; border:none; font-size:1.8rem; cursor:pointer; color:#666; line-height:1;">&times;</button>
                    </div>
                    <p id="picker-date-label" style="color:#666; font-size:0.9rem; margin-bottom:1rem;"></p>
                    <div id="picker-list"></div>
                </div>
            `;
            document.body.appendChild(picker);

            document.getElementById('picker-close-btn').addEventListener('click', () => {
                picker.style.display = 'none';
            });
            picker.addEventListener('click', (e) => {
                if (e.target === picker) picker.style.display = 'none';
            });
        }

        const [year, month, day] = dateStr.split('-');
        document.getElementById('picker-date-label').textContent =
            `${activites.length} activités le ${day}/${month}/${year} — sélectionnez-en une :`;

        const list = document.getElementById('picker-list');
        list.innerHTML = '';
        activites.forEach((act, idx) => {
            const config = TYPES_CONFIG[act.type] || TYPES_CONFIG['autre'];
            const btn = document.createElement('button');
            btn.style.cssText = `
                display:flex; align-items:center; gap:0.75rem; width:100%;
                padding:0.75rem 1rem; margin-bottom:0.5rem; border-radius:8px;
                border:2px solid #e0e0e0; background:#f8fafc; cursor:pointer;
                text-align:left; transition:all 0.15s; font-size:0.9rem;
            `;
            btn.innerHTML = `
                <span style="width:12px; height:12px; border-radius:50%; background:${config.couleur}; flex-shrink:0;"></span>
                <span><strong>${config.nom}</strong> — 📁 ${act.dossier}${act.commentaire ? `<br><small style="color:#888">${act.commentaire}</small>` : ''}</span>
            `;
            btn.addEventListener('mouseenter', () => btn.style.borderColor = config.couleur);
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
            state.date = new Date(state.currYear, newMonth, new Date().getDate());
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

    const modal = document.getElementById('activity-modal');
    const openBtn = document.getElementById('add-activity-btn');
    const closeBtn = document.getElementById('close-modal-btn');
    const cancelBtn = document.getElementById('cancel-activity-btn');
    const deleteBtn = document.getElementById('delete-activity-btn');
    const form = document.getElementById('activity-form');
    const statusDiv = document.getElementById('activity-form-status');

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
        console.log('Clic sur le bouton détecté !');
        // Remettre le titre par défaut
        const modalTitle = modal.querySelector('.activity-modal-header h3');
        if (modalTitle) modalTitle.innerHTML = '<i class="bi bi-calendar-plus"></i> Nouvelle activité';
        form.reset();
        modal.style.display = 'flex';
        const now = new Date();
        const dateString = now.toISOString().slice(0, 16);
        document.getElementById('activity-date').value = dateString;
    });

    function closeModal() {
        modal.style.display = 'none';
        form.reset();
        statusDiv.style.display = 'none';
    }

    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);


    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });

    deleteBtn.addEventListener('click', function() {
        const formData = {
            dossier: document.getElementById('activity-dossier').value.trim(),
            type: document.getElementById('activity-type').value,
            date: document.getElementById('activity-date').value,
            commentaire: document.getElementById('activity-commentaire').value.trim()
        };


        if (!formData.dossier || !formData.type || !formData.date) {
            showStatus('Veuillez remplir tous les champs obligatoires pour supprimer', 'error');
            return;
        }


        if (!confirm(`Êtes-vous sûr de vouloir supprimer l'activité correspondant à ces critères ?\n\nDossier: ${formData.dossier}\nType: ${formData.type}\nDate: ${formData.date}`)) {
            return;
        }

        // Désactiver le bouton pendant l'envoi
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Suppression...';

        // Récupérer le token CSRF
        const csrftoken = getCookie('csrftoken');

        // Envoyer la requête
        fetch('/api/delete-activity/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            deleteBtn.disabled = false;
            deleteBtn.innerHTML = '<i class="bi bi-trash"></i> Supprimer';

            if (data.success) {
                showStatus(`${data.deleted_count} activité(s) supprimée(s) avec succès !`, 'success');

                // Recharger le calendrier après 1 seconde
                setTimeout(() => {
                    closeModal();
                    location.reload();
                }, 1000);
            } else {
                showStatus( (data.message || 'Erreur lors de la suppression'), 'error');
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
            dossier: document.getElementById('activity-dossier').value.trim(),
            type: document.getElementById('activity-type').value,
            date: document.getElementById('activity-date').value,
            commentaire: document.getElementById('activity-commentaire').value.trim()
        };

        if (!formData.dossier || !formData.type || !formData.date) {
            showStatus('Veuillez remplir tous les champs obligatoires', 'error');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Enregistrement...';

        const csrftoken = getCookie('csrftoken');

        fetch('/api/create-activity/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-check-circle"></i> Enregistrer';

            if (data.success) {
                showStatus(' Activité créée avec succès !', 'success');

                setTimeout(() => {
                    closeModal();
                    location.reload();
                }, 1000);
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
        statusDiv.className = type;
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