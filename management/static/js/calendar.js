/**
 * Calendrier avec activités - Version simplifiée
 * Encercle les dates qui ont des activités (comme la date actuelle)
 */

(function() {
    // ========================================================================
    // CONFIGURATION VERSION FINALE
    // ========================================================================

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

    // ========================================================================
    // ÉTAT GLOBAL
    // ========================================================================

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

    // ========================================================================
    // CHARGEMENT DES ACTIVITÉS
    // ========================================================================

    async function loadActivities(month, year) {
        try {
            console.log(`📅 Chargement activités pour ${month + 1}/${year}`);

            const response = await fetch(
                `/api/calendar-activities/?month=${month + 1}&year=${year}`
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                state.activites = data.activites;
                console.log(`✅ ${data.activites.length} activités chargées`);
                console.log('Activités:', state.activites);

                // Initialiser les filtres
                initFilters();

                // Rendre le calendrier
                renderCalendar();
            } else {
                console.error('❌ Erreur API:', data.message);
                state.activites = [];
                renderCalendar();
            }
        } catch (error) {
            console.error('❌ Erreur chargement activités:', error);
            state.activites = [];
            renderCalendar();
        }
    }

    // ========================================================================
    // GESTION DES FILTRES
    // ========================================================================

    function initFilters() {
        // Extraire les types uniques
        const typesUniques = [...new Set(state.activites.map(a => a.type))];

        // Extraire les dossiers uniques
        const dossiersUniques = [...new Set(state.activites.map(a => a.dossier))];

        // Initialiser tous les filtres à true
        state.filtresTypes = {};
        typesUniques.forEach(type => {
            state.filtresTypes[type] = true;
        });

        state.filtresDossiers = {};
        dossiersUniques.forEach(dossier => {
            state.filtresDossiers[dossier] = true;
        });

        console.log('Filtres types:', state.filtresTypes);
        console.log('Filtres dossiers:', state.filtresDossiers);

        // Rendre les filtres
        renderFilters(typesUniques, dossiersUniques);
    }

    function renderFilters(types, dossiers) {
        // Trouver le conteneur des filtres (doit exister dans le HTML)
        let filtersContainer = document.querySelector('.calendar-filters');

        if (!filtersContainer) {
            console.warn('⚠️  Conteneur .calendar-filters non trouvé');
            return;
        }

        // Construire le HTML des filtres
        let filtersHTML = '<div class="filters-content">';

        // Section Types
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

        // Section Dossiers
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

        // Attacher les événements
        attachFilterEvents();
    }

    function attachFilterEvents() {
        const checkboxes = document.querySelectorAll('.calendar-filters input[type="checkbox"]');

        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const filterType = this.dataset.filterType;
                const value = this.dataset.value;
                const isChecked = this.checked;

                console.log(`Filtre ${filterType}:${value} = ${isChecked}`);

                if (filterType === 'type') {
                    state.filtresTypes[value] = isChecked;
                } else if (filterType === 'dossier') {
                    state.filtresDossiers[value] = isChecked;
                }

                // Rerendre le calendrier
                renderCalendar();
            });
        });
    }

    // ========================================================================
    // VÉRIFIER SI UNE DATE A DES ACTIVITÉS FILTRÉES
    // ========================================================================

    function hasActivities(dateStr) {
        console.log(`🔍 Vérification activités pour ${dateStr}`);

        const activites = state.activites.filter(act => {
            // Date correspond ?
            if (act.date !== dateStr) {
                return false;
            }

            // Type filtré ?
            if (!state.filtresTypes[act.type]) {
                console.log(`  ❌ Type ${act.type} filtré`);
                return false;
            }

            // Dossier filtré ?
            if (!state.filtresDossiers[act.dossier]) {
                console.log(`  ❌ Dossier ${act.dossier} filtré`);
                return false;
            }

            return true;
        });

        console.log(`  ✅ ${activites.length} activités trouvées`);
        return activites.length > 0;
    }

    // ========================================================================
    // RENDU DU CALENDRIER
    // ========================================================================

    function renderCalendar() {
        console.log('🎨 Rendu du calendrier');

        let firstDayOfMonth = new Date(state.currYear, state.currMonth, 0).getDay();
        let lastDateOfMonth = new Date(state.currYear, state.currMonth + 1, 0).getDate();
        let lastDayOfMonth = new Date(state.currYear, state.currMonth, lastDateOfMonth).getDay();
        let lastDateOfLastMonth = new Date(state.currYear, state.currMonth, 0).getDate();

        days.innerHTML = "";
        let weekCounter = 0;
        let ul = document.createElement("ul");

        // Jours du mois précédent
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

        // Jours du mois actuel
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

        // Jours du mois suivant
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

        console.log('✅ Calendrier rendu');
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
            // Construire la date au format YYYY-MM-DD
            const dateStr = `${state.currYear}-${String(state.currMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

            console.log(`Jour ${day}: dateStr = ${dateStr}`);

            // Vérifier si c'est aujourd'hui
            if (day === state.date.getDate() &&
                state.currMonth === new Date().getMonth() &&
                state.currYear === new Date().getFullYear()) {
                li.classList.add("current");
                console.log(`  → Aujourd'hui`);
            }

            // Vérifier si cette date a des activités
            if (hasActivities(dateStr)) {
                li.classList.add("has-activity");
                console.log(`  → A des activités`);
            }

            li.addEventListener("click", () => {
                li.classList.add("active");
                let currentActive = document.querySelectorAll(".active");
                currentActive.forEach((activeEle) => {
                    if (activeEle !== li) activeEle.classList.remove("active");
                });
            });
        }

        return li;
    }

    // ========================================================================
    // NAVIGATION
    // ========================================================================

    function changeMonth(newMonth) {
        if (newMonth < 0 || newMonth > 11) {
            state.date = new Date(state.currYear, newMonth, new Date().getDate());
            state.currYear = state.date.getFullYear();
            state.currMonth = state.date.getMonth();
        } else {
            state.date = new Date();
        }

        // Recharger les activités
        loadActivities(state.currMonth, state.currYear);
    }

    // ========================================================================
    // INITIALISATION
    // ========================================================================

    console.log('🚀 Initialisation du calendrier');

    // Charger les activités au démarrage
    loadActivities(state.currMonth, state.currYear);

    // Attacher les événements de navigation
    prevNextIcon.forEach(icon => {
        icon.addEventListener("click", () => {
            state.currMonth = (icon.id === "prev" ? (state.currMonth - 1) : (state.currMonth + 1));
            changeMonth(state.currMonth);
        });
    });

})();