(function() {
    const dataNode = document.getElementById('admin-projects-data');
    const customFieldsNode = document.getElementById('admin-custom-fields-data');
    let projects = dataNode ? JSON.parse(dataNode.textContent) : [];
    let customFields = customFieldsNode ? JSON.parse(customFieldsNode.textContent) : [];

    const tbody = document.getElementById('projects-table-body');
    const tableHead = document.getElementById('projects-table-head');
    const emptyState = document.getElementById('projects-empty-state');
    const searchInput = document.getElementById('project-search');
    const typeFilter = document.getElementById('project-type-filter');
    const activiteFilter = document.getElementById('project-activite-filter');
    const etatFilter = document.getElementById('project-etat-filter');
    const categorieFilter = document.getElementById('project-categorie-filter');
    const minPriceFilter = document.getElementById('project-min-price-filter');
    const maxPriceFilter = document.getElementById('project-max-price-filter');
    const promiseFromFilter = document.getElementById('project-promise-from-filter');
    const promiseToFilter = document.getElementById('project-promise-to-filter');
    const activitiesFilter = document.getElementById('project-activities-filter');
    const resetFiltersBtn = document.getElementById('project-reset-filters');
    const modal = document.getElementById('project-modal');
    const form = document.getElementById('project-form');
    const status = document.getElementById('project-form-status');
    const addBtn = document.getElementById('add-project-btn');
    const closeBtn = document.getElementById('close-project-modal-btn');
    const cancelBtn = document.getElementById('cancel-project-btn');
    const deleteBtn = document.getElementById('delete-project-btn');
    const activityScopeElements = document.querySelectorAll('[data-activity-scope]');
    const projectCustomFieldsSection = document.getElementById('project-custom-fields-section');
    const projectCustomFieldsContainer = document.getElementById('project-custom-fields-container');
    const customFieldsTbody = document.getElementById('custom-fields-table-body');
    const customFieldModal = document.getElementById('custom-field-modal');
    const customFieldForm = document.getElementById('custom-field-form');
    const customFieldStatus = document.getElementById('custom-field-form-status');
    const addCustomFieldBtn = document.getElementById('add-custom-field-btn');
    const closeCustomFieldBtn = document.getElementById('close-custom-field-modal-btn');
    const cancelCustomFieldBtn = document.getElementById('cancel-custom-field-btn');

    const fields = {
        id: document.getElementById('project-id'),
        reference: document.getElementById('project-reference'),
        affaire: document.getElementById('project-affaire'),
        type: document.getElementById('project-type'),
        activiteMetier: document.getElementById('project-activite-metier'),
        etat: document.getElementById('project-etat'),
        categorie: document.getElementById('project-categorie'),
        lotEtage: document.getElementById('project-lot-etage'),
        adresseBien: document.getElementById('project-adresse-bien'),
        parcelles: document.getElementById('project-parcelles'),
        vendeur: document.getElementById('project-vendeur'),
        beneficiaire: document.getElementById('project-beneficiaire'),
        locataire: document.getElementById('project-locataire'),
        datePromesse: document.getElementById('project-date-promesse'),
        premierePeriode: document.getElementById('project-premiere-periode'),
        deuxiemePeriode: document.getElementById('project-deuxieme-periode'),
        avenant1: document.getElementById('project-avenant-1'),
        avenant2: document.getElementById('project-avenant-2'),
        avenant3: document.getElementById('project-avenant-3'),
        negociationExterne: document.getElementById('project-negociation-externe'),
        frais: document.getElementById('project-frais'),
        prix: document.getElementById('project-prix'),
        dg: document.getElementById('project-dg'),
        dateDg: document.getElementById('project-date-dg'),
        depotPermis: document.getElementById('project-depot-permis'),
        obtentionPermis: document.getElementById('project-obtention-permis'),
        diags: document.getElementById('project-diags'),
        bornage: document.getElementById('project-bornage'),
        etudeSolGeotechnique: document.getElementById('project-etude-sol-geotechnique'),
        etudePollution: document.getElementById('project-etude-pollution'),
        etudeImpact: document.getElementById('project-etude-impact'),
        prorogation: document.getElementById('project-prorogation'),
        csPret: document.getElementById('project-cs-pret'),
        dateCsPret: document.getElementById('project-date-cs-pret'),
        dateReiteration: document.getElementById('project-date-reiteration'),
        acte: document.getElementById('project-acte'),
        relevesCompte: document.getElementById('project-releves-compte'),
        title: document.getElementById('project-modal-title'),
    };

    const customFieldInputs = {
        id: document.getElementById('custom-field-id'),
        title: document.getElementById('custom-field-modal-title'),
        label: document.getElementById('custom-field-label'),
        type: document.getElementById('custom-field-type'),
        activiteMetier: document.getElementById('custom-field-activite-metier'),
        sortOrder: document.getElementById('custom-field-sort-order'),
        choices: document.getElementById('custom-field-choices'),
        choicesGroup: document.getElementById('custom-field-choices-group'),
        showDetail: document.getElementById('custom-field-show-detail'),
        showTable: document.getElementById('custom-field-show-table'),
        active: document.getElementById('custom-field-active'),
    };

    function csrftoken() {
        const row = document.cookie.split('; ').find(item => item.startsWith('csrftoken='));
        return row ? decodeURIComponent(row.split('=')[1]) : '';
    }

    function escapeHtml(value) {
        return String(value || '').replace(/[&<>"']/g, char => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[char]));
    }

    function money(value) {
        const amount = Number(value || 0);
        return amount.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
    }

    function showStatus(message, isError) {
        status.textContent = message;
        status.className = isError ? 'project-status error' : 'project-status success';
        status.style.display = 'block';
    }

    function clearStatus() {
        status.textContent = '';
        status.className = '';
        status.style.display = 'none';
    }

    function showCustomFieldStatus(message, isError) {
        customFieldStatus.textContent = message;
        customFieldStatus.className = isError ? 'project-status error' : 'project-status success';
        customFieldStatus.style.display = 'block';
    }

    function clearCustomFieldStatus() {
        customFieldStatus.textContent = '';
        customFieldStatus.className = '';
        customFieldStatus.style.display = 'none';
    }

    function fieldMatchesActivity(field, activiteMetier) {
        return !field.activite_metier || field.activite_metier === activiteMetier;
    }

    function activeCustomFields(activiteMetier) {
        return customFields
            .filter(field => field.is_active && (activiteMetier === undefined || fieldMatchesActivity(field, activiteMetier)))
            .sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0) || a.label.localeCompare(b.label));
    }

    function tableCustomFields() {
        return activeCustomFields().filter(field => field.show_in_table);
    }

    function customDisplayValue(field, value) {
        if (value === undefined || value === null || value === '') return '';
        if (field.field_type === 'checkbox') return ['true', '1', 'on', 'yes', 'oui'].includes(String(value).toLowerCase()) ? 'Oui' : 'Non';
        if (field.field_type === 'amount') return money(value);
        return String(value);
    }

    function renderProjectsHeader() {
        if (!tableHead) return;
        const customHeaders = tableCustomFields()
            .map(field => `<th>${escapeHtml(field.label)}</th>`)
            .join('');
        tableHead.innerHTML = `
            <th>Référence</th>
            <th>Affaire</th>
            <th>Type</th>
            <th>Activité</th>
            <th>État</th>
            <th>Catégorie</th>
            <th>Prix</th>
            ${customHeaders}
            <th>Activités</th>
            <th>Actions</th>
        `;
    }

    function renderCustomFieldsManager() {
        if (!customFieldsTbody) return;
        const sortedFields = [...customFields].sort(
            (a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0) || a.label.localeCompare(b.label)
        );
        customFieldsTbody.innerHTML = sortedFields.map(field => {
            const displays = [
                field.show_in_detail ? 'Fiche' : '',
                field.show_in_table ? 'Tableau' : '',
            ].filter(Boolean).join(' + ') || '-';
            return `
                <tr>
                    <td><strong>${escapeHtml(field.label)}</strong></td>
                    <td>${escapeHtml(field.activite_metier_label || 'Toutes les activités')}</td>
                    <td>${escapeHtml(field.field_type_label || field.field_type)}</td>
                    <td>${escapeHtml(displays)}</td>
                    <td>${field.is_active ? '<span class="status-badge">Actif</span>' : '<span class="status-badge" style="background:#fee2e2;color:#991b1b;">Désactivé</span>'}</td>
                    <td style="display:flex;gap:.5rem;flex-wrap:wrap;">
                        <button type="button" class="btn btn-secondary custom-field-edit-btn" data-field-id="${field.id}">
                            <i class="bi bi-pencil-square"></i> Modifier
                        </button>
                        <button type="button" class="btn btn-secondary custom-field-toggle-btn" data-field-id="${field.id}">
                            <i class="bi ${field.is_active ? 'bi-eye-slash' : 'bi-eye'}"></i> ${field.is_active ? 'Désactiver' : 'Réactiver'}
                        </button>
                    </td>
                </tr>
            `;
        }).join('') || `
            <tr>
                <td colspan="6" style="text-align:center;color:var(--text-secondary);padding:1rem;">
                    Aucun champ personnalisé.
                </td>
            </tr>
        `;
    }

    function inputTypeForField(field) {
        if (field.field_type === 'date') return 'date';
        if (field.field_type === 'amount' || field.field_type === 'number') return 'number';
        return 'text';
    }

    function renderProjectCustomFields(project) {
        if (!projectCustomFieldsContainer || !projectCustomFieldsSection) return;
        const selectedActivity = fields.activiteMetier?.value || project?.activite_metier || '';
        const fieldsToRender = activeCustomFields(selectedActivity);
        projectCustomFieldsSection.style.display = fieldsToRender.length ? 'block' : 'none';
        projectCustomFieldsContainer.innerHTML = fieldsToRender.map(field => {
            const value = project?.custom_fields?.[String(field.id)] || '';
            if (field.field_type === 'checkbox') {
                const checked = ['true', '1', 'on', 'yes', 'oui'].includes(String(value).toLowerCase()) ? 'checked' : '';
                return `
                    <div class="form-group">
                        <label class="form-label">${escapeHtml(field.label)}</label>
                        <label style="display:flex;align-items:center;gap:.5rem;margin-top:.65rem;">
                            <input type="checkbox" class="project-custom-field" data-field-id="${field.id}" ${checked}>
                            Oui
                        </label>
                    </div>
                `;
            }
            if (field.field_type === 'choice') {
                const options = (field.choices || []).map(choice => `
                    <option value="${escapeHtml(choice)}" ${choice === value ? 'selected' : ''}>${escapeHtml(choice)}</option>
                `).join('');
                return `
                    <div class="form-group">
                        <label class="form-label">${escapeHtml(field.label)}</label>
                        <select class="form-control project-custom-field" data-field-id="${field.id}">
                            <option value="">-- Aucun --</option>
                            ${options}
                        </select>
                    </div>
                `;
            }
            const step = field.field_type === 'amount' ? '0.01' : (field.field_type === 'number' ? 'any' : '');
            return `
                <div class="form-group">
                    <label class="form-label">${escapeHtml(field.label)}</label>
                    <input type="${inputTypeForField(field)}" class="form-control project-custom-field"
                           data-field-id="${field.id}" value="${escapeHtml(value)}" ${step ? `step="${step}"` : ''}>
                </div>
            `;
        }).join('');
    }

    function renderProjects() {
        if (!tbody) return;
        renderProjectsHeader();
        const q = (searchInput?.value || '').trim().toLowerCase();
        const selectedType = typeFilter?.value || '';
        const selectedActivite = activiteFilter?.value || '';
        const selectedEtat = etatFilter?.value || '';
        const selectedCategorie = categorieFilter?.value || '';
        const minPrice = Number(minPriceFilter?.value || 0);
        const maxPrice = Number(maxPriceFilter?.value || 0);
        const promiseFrom = promiseFromFilter?.value || '';
        const promiseTo = promiseToFilter?.value || '';
        const selectedActivities = activitiesFilter?.value || '';
        const filtered = projects.filter(project => {
            const matchesQuery = !q
                || (project.reference || '').toLowerCase().includes(q)
                || (project.affaire || project.name || '').toLowerCase().includes(q)
                || (project.adresse_bien || '').toLowerCase().includes(q)
                || (project.vendeur || '').toLowerCase().includes(q)
                || (project.beneficiaire || '').toLowerCase().includes(q)
                || (project.locataire || '').toLowerCase().includes(q)
                || (project.lot_etage || '').toLowerCase().includes(q)
                || (project.type_dossier_label || project.type_label || '').toLowerCase().includes(q)
                || (project.activite_metier_label || '').toLowerCase().includes(q)
                || (project.etat_label || '').toLowerCase().includes(q)
                || (project.categorie_label || '').toLowerCase().includes(q);
            const matchesType = !selectedType || project.type_dossier === selectedType || project.type === selectedType;
            const matchesActivite = !selectedActivite || project.activite_metier === selectedActivite;
            const matchesEtat = !selectedEtat || project.etat === selectedEtat;
            const matchesCategorie = !selectedCategorie || String(project.categorie_id || '') === selectedCategorie;
            const price = Number(project.prix || project.total_estimated || 0);
            const matchesMinPrice = !minPrice || price >= minPrice;
            const matchesMaxPrice = !maxPrice || price <= maxPrice;
            const promiseDate = project.date_promesse || '';
            const matchesPromiseFrom = !promiseFrom || (promiseDate && promiseDate >= promiseFrom);
            const matchesPromiseTo = !promiseTo || (promiseDate && promiseDate <= promiseTo);
            const activitiesCount = Number(project.activities_count || 0);
            const matchesActivities = !selectedActivities
                || (selectedActivities === 'with' && activitiesCount > 0)
                || (selectedActivities === 'without' && activitiesCount === 0);
            return matchesQuery
                && matchesType
                && matchesActivite
                && matchesEtat
                && matchesCategorie
                && matchesMinPrice
                && matchesMaxPrice
                && matchesPromiseFrom
                && matchesPromiseTo
                && matchesActivities;
        });

        tbody.innerHTML = filtered.map(project => {
            const customCells = tableCustomFields().map(field => `
                <td>${fieldMatchesActivity(field, project.activite_metier) ? escapeHtml(customDisplayValue(field, project.custom_fields?.[String(field.id)])) : ''}</td>
            `).join('');
            return `
            <tr>
                <td><strong>${escapeHtml(project.reference)}</strong></td>
                <td>${escapeHtml(project.affaire || project.name)}</td>
                <td><span class="status-badge">${escapeHtml(project.type_dossier_label || project.type_label)}</span></td>
                <td>${escapeHtml(project.activite_metier_label)}</td>
                <td>${escapeHtml(project.etat_label)}</td>
                <td>${escapeHtml(project.categorie_label || 'Non classé')}</td>
                <td>${money(project.prix)}</td>
                ${customCells}
                <td>${project.activities_count || 0}</td>
                <td style="display:flex;gap:.5rem;flex-wrap:wrap;">
                    <a class="btn btn-secondary" href="/administratif/dossiers/${project.id}/">
                        <i class="bi bi-eye"></i> Voir
                    </a>
                    <button type="button" class="btn btn-secondary project-edit-btn" data-project-id="${project.id}">
                        <i class="bi bi-pencil-square"></i> Modifier
                    </button>
                </td>
            </tr>
        `;
        }).join('');

        if (emptyState) {
            emptyState.style.display = filtered.length ? 'none' : 'block';
        }
    }

    function resetFilters() {
        [
            searchInput,
            typeFilter,
            activiteFilter,
            etatFilter,
            categorieFilter,
            minPriceFilter,
            maxPriceFilter,
            promiseFromFilter,
            promiseToFilter,
            activitiesFilter,
        ].forEach(input => {
            if (input) input.value = '';
        });
        renderProjects();
    }

    function setValue(input, value) {
        if (input) input.value = value || '';
    }

    function syncActivityFields() {
        const activity = fields.activiteMetier?.value || '';
        activityScopeElements.forEach(element => {
            const scopes = (element.dataset.activityScope || '').split(/\s+/).filter(Boolean);
            const shouldShow = scopes.includes(activity) || (scopes.includes('general') && activity !== 'promotion_immobiliere');
            element.style.display = shouldShow ? '' : 'none';
        });
    }

    function openProjectModal(project) {
        clearStatus();
        setValue(fields.id, project?.id);
        setValue(fields.reference, project?.reference);
        setValue(fields.affaire, project?.affaire || project?.name);
        setValue(fields.type, project?.type_dossier || project?.type || 'vente');
        setValue(fields.activiteMetier, project?.activite_metier || 'marchand_biens');
        setValue(fields.etat, project?.etat || 'promesse');
        setValue(fields.categorie, project?.categorie_id || fields.categorie?.options?.[0]?.value);
        setValue(fields.lotEtage, project?.lot_etage);
        setValue(fields.adresseBien, project?.adresse_bien);
        setValue(fields.parcelles, project?.parcelles);
        setValue(fields.vendeur, project?.vendeur);
        setValue(fields.beneficiaire, project?.beneficiaire);
        setValue(fields.locataire, project?.locataire);
        setValue(fields.datePromesse, project?.date_promesse);
        setValue(fields.premierePeriode, project?.premiere_periode);
        setValue(fields.deuxiemePeriode, project?.deuxieme_periode);
        setValue(fields.avenant1, project?.avenant_1);
        setValue(fields.avenant2, project?.avenant_2);
        setValue(fields.avenant3, project?.avenant_3);
        setValue(fields.negociationExterne, project?.negociation_externe);
        setValue(fields.frais, project?.frais || '0');
        setValue(fields.prix, project?.prix || project?.total_estimated || '0');
        setValue(fields.dg, project?.dg || '0');
        setValue(fields.dateDg, project?.date_dg);
        setValue(fields.depotPermis, project?.depot_permis);
        setValue(fields.obtentionPermis, project?.obtention_permis);
        setValue(fields.diags, project?.diags);
        setValue(fields.bornage, project?.bornage);
        setValue(fields.etudeSolGeotechnique, project?.etude_sol_geotechnique);
        setValue(fields.etudePollution, project?.etude_pollution);
        setValue(fields.etudeImpact, project?.etude_impact);
        setValue(fields.prorogation, project?.prorogation);
        setValue(fields.csPret, project?.cs_pret);
        setValue(fields.dateCsPret, project?.date_cs_pret);
        setValue(fields.dateReiteration, project?.date_reiteration);
        setValue(fields.acte, project?.acte);
        setValue(fields.relevesCompte, project?.releves_compte);
        renderProjectCustomFields(project);
        syncActivityFields();
        fields.title.innerHTML = project
            ? '<i class="bi bi-pencil-square"></i> Modifier le dossier'
            : '<i class="bi bi-folder-plus"></i> Nouveau dossier';
        deleteBtn.style.display = project ? 'inline-flex' : 'none';
        modal.style.display = 'flex';
        fields.reference.focus();
    }

    function closeProjectModal() {
        modal.style.display = 'none';
        form.reset();
        clearStatus();
    }

    function buildPayload() {
        const customFieldValues = {};
        document.querySelectorAll('.project-custom-field').forEach(input => {
            customFieldValues[input.dataset.fieldId] = input.type === 'checkbox' ? input.checked : input.value;
        });
        return {
            reference: fields.reference.value,
            affaire: fields.affaire.value,
            type_dossier: fields.type.value,
            activite_metier: fields.activiteMetier.value,
            etat: fields.etat.value,
            categorie_id: fields.categorie.value,
            lot_etage: fields.lotEtage.value,
            adresse_bien: fields.adresseBien.value,
            parcelles: fields.parcelles.value,
            vendeur: fields.vendeur.value,
            beneficiaire: fields.beneficiaire.value,
            locataire: fields.locataire.value,
            date_promesse: fields.datePromesse.value,
            premiere_periode: fields.premierePeriode.value,
            deuxieme_periode: fields.deuxiemePeriode.value,
            avenant_1: fields.avenant1.value,
            avenant_2: fields.avenant2.value,
            avenant_3: fields.avenant3.value,
            negociation_externe: fields.negociationExterne.value,
            frais: fields.frais.value || '0',
            prix: fields.prix.value || '0',
            dg: fields.dg.value || '0',
            date_dg: fields.dateDg.value,
            depot_permis: fields.depotPermis.value,
            obtention_permis: fields.obtentionPermis.value,
            diags: fields.diags.value,
            bornage: fields.bornage.value,
            etude_sol_geotechnique: fields.etudeSolGeotechnique.value,
            etude_pollution: fields.etudePollution.value,
            etude_impact: fields.etudeImpact.value,
            prorogation: fields.prorogation.value,
            cs_pret: fields.csPret.value,
            date_cs_pret: fields.dateCsPret.value,
            date_reiteration: fields.dateReiteration.value,
            acte: fields.acte.value,
            releves_compte: fields.relevesCompte.value,
            custom_fields: customFieldValues,
        };
    }

    async function submitProject(event) {
        event.preventDefault();
        clearStatus();

        const id = fields.id.value;
        const url = id ? `/api/admin-projects/${id}/update/` : '/api/admin-projects/create/';

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken(),
                },
                body: JSON.stringify(buildPayload()),
            });
            const data = await response.json();
            if (!data.success) throw new Error(data.message || 'Enregistrement impossible');

            const dossier = data.dossier || data.project;
            const existingIndex = projects.findIndex(project => String(project.id) === String(dossier.id));
            if (existingIndex >= 0) {
                projects[existingIndex] = dossier;
            } else {
                projects.push(dossier);
            }
            projects.sort((a, b) => a.reference.localeCompare(b.reference));
            renderProjects();
            closeProjectModal();
        } catch (error) {
            showStatus(error.message, true);
        }
    }

    async function deleteProject() {
        const id = fields.id.value;
        if (!id) return;
        const project = projects.find(item => String(item.id) === String(id));
        if (!confirm(`Supprimer le dossier ${project?.reference || ''} ?`)) return;

        try {
            const response = await fetch(`/api/admin-projects/${id}/delete/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken() },
            });
            const data = await response.json();
            if (!data.success) throw new Error(data.message || 'Suppression impossible');

            projects = projects.filter(item => String(item.id) !== String(id));
            renderProjects();
            closeProjectModal();
        } catch (error) {
            showStatus(error.message, true);
        }
    }

    function syncCustomFieldType() {
        const isChoice = customFieldInputs.type?.value === 'choice';
        if (customFieldInputs.choicesGroup) {
            customFieldInputs.choicesGroup.style.display = isChoice ? 'block' : 'none';
        }
    }

    function openCustomFieldModal(field) {
        clearCustomFieldStatus();
        setValue(customFieldInputs.id, field?.id);
        setValue(customFieldInputs.label, field?.label);
        setValue(customFieldInputs.type, field?.field_type || 'text');
        setValue(customFieldInputs.activiteMetier, field?.activite_metier || '');
        setValue(customFieldInputs.sortOrder, field?.sort_order || '0');
        setValue(customFieldInputs.choices, field?.choices_text || (field?.choices || []).join('\n'));
        customFieldInputs.showDetail.checked = field ? Boolean(field.show_in_detail) : true;
        customFieldInputs.showTable.checked = field ? Boolean(field.show_in_table) : false;
        customFieldInputs.active.checked = field ? Boolean(field.is_active) : true;
        customFieldInputs.title.innerHTML = field
            ? '<i class="bi bi-pencil-square"></i> Modifier le champ personnalisé'
            : '<i class="bi bi-ui-checks-grid"></i> Nouveau champ personnalisé';
        syncCustomFieldType();
        customFieldModal.style.display = 'flex';
        customFieldInputs.label.focus();
    }

    function closeCustomFieldModal() {
        customFieldModal.style.display = 'none';
        customFieldForm.reset();
        clearCustomFieldStatus();
        syncCustomFieldType();
    }

    function buildCustomFieldPayload(override) {
        return {
            label: customFieldInputs.label.value,
            field_type: customFieldInputs.type.value,
            activite_metier: customFieldInputs.activiteMetier.value,
            sort_order: customFieldInputs.sortOrder.value || '0',
            choices: customFieldInputs.choices.value,
            show_in_detail: customFieldInputs.showDetail.checked,
            show_in_table: customFieldInputs.showTable.checked,
            is_active: customFieldInputs.active.checked,
            ...(override || {}),
        };
    }

    async function saveCustomField(payload, id) {
        const url = id ? `/api/admin-custom-fields/${id}/update/` : '/api/admin-custom-fields/create/';
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken(),
            },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!data.success) throw new Error(data.message || 'Enregistrement impossible');
        const field = data.field;
        const existingIndex = customFields.findIndex(item => String(item.id) === String(field.id));
        if (existingIndex >= 0) {
            customFields[existingIndex] = field;
        } else {
            customFields.push(field);
        }
        renderCustomFieldsManager();
        renderProjects();
    }

    async function submitCustomField(event) {
        event.preventDefault();
        clearCustomFieldStatus();
        const id = customFieldInputs.id.value;
        try {
            await saveCustomField(buildCustomFieldPayload(), id);
            closeCustomFieldModal();
        } catch (error) {
            showCustomFieldStatus(error.message, true);
        }
    }

    async function toggleCustomField(field) {
        try {
            await saveCustomField(
                {
                    label: field.label,
                    field_type: field.field_type,
                    activite_metier: field.activite_metier || '',
                    choices: field.choices_text || (field.choices || []).join('\n'),
                    show_in_detail: field.show_in_detail,
                    show_in_table: field.show_in_table,
                    is_active: !field.is_active,
                    sort_order: field.sort_order || 0,
                },
                field.id
            );
        } catch (error) {
            alert(error.message);
        }
    }

    addBtn?.addEventListener('click', () => openProjectModal(null));
    closeBtn?.addEventListener('click', closeProjectModal);
    cancelBtn?.addEventListener('click', closeProjectModal);
    form?.addEventListener('submit', submitProject);
    deleteBtn?.addEventListener('click', deleteProject);
    addCustomFieldBtn?.addEventListener('click', () => openCustomFieldModal(null));
    closeCustomFieldBtn?.addEventListener('click', closeCustomFieldModal);
    cancelCustomFieldBtn?.addEventListener('click', closeCustomFieldModal);
    customFieldForm?.addEventListener('submit', submitCustomField);
    customFieldInputs.type?.addEventListener('change', syncCustomFieldType);
    searchInput?.addEventListener('input', renderProjects);
    fields.activiteMetier?.addEventListener('input', () => {
        syncActivityFields();
        renderProjectCustomFields(null);
    });
    fields.activiteMetier?.addEventListener('change', () => {
        syncActivityFields();
        renderProjectCustomFields(null);
    });
    activiteFilter?.addEventListener('input', () => {
        renderProjects();
    });
    activiteFilter?.addEventListener('change', () => {
        renderProjects();
    });
    [
        typeFilter,
        etatFilter,
        categorieFilter,
        minPriceFilter,
        maxPriceFilter,
        promiseFromFilter,
        promiseToFilter,
        activitiesFilter,
    ].forEach(input => {
        input?.addEventListener('input', renderProjects);
        input?.addEventListener('change', renderProjects);
    });
    resetFiltersBtn?.addEventListener('click', resetFilters);

    customFieldsTbody?.addEventListener('click', event => {
        const editBtn = event.target.closest('.custom-field-edit-btn');
        const toggleBtn = event.target.closest('.custom-field-toggle-btn');
        const button = editBtn || toggleBtn;
        if (!button) return;
        const field = customFields.find(item => String(item.id) === String(button.dataset.fieldId));
        if (!field) return;
        if (editBtn) {
            openCustomFieldModal(field);
        } else {
            toggleCustomField(field);
        }
    });

    tbody?.addEventListener('click', event => {
        const btn = event.target.closest('.project-edit-btn');
        if (!btn) return;
        const project = projects.find(item => String(item.id) === String(btn.dataset.projectId));
        if (project) openProjectModal(project);
    });

    modal?.addEventListener('click', event => {
        if (event.target === modal) closeProjectModal();
    });

    customFieldModal?.addEventListener('click', event => {
        if (event.target === customFieldModal) closeCustomFieldModal();
    });

    syncActivityFields();
    syncCustomFieldType();
    renderCustomFieldsManager();
    renderProjects();
})();
