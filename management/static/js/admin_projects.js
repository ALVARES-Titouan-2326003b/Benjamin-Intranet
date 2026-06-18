(function() {
    const dataNode = document.getElementById('admin-projects-data');
    let projects = dataNode ? JSON.parse(dataNode.textContent) : [];

    const tbody = document.getElementById('projects-table-body');
    const emptyState = document.getElementById('projects-empty-state');
    const searchInput = document.getElementById('project-search');
    const typeFilter = document.getElementById('project-type-filter');
    const modal = document.getElementById('project-modal');
    const form = document.getElementById('project-form');
    const status = document.getElementById('project-form-status');
    const addBtn = document.getElementById('add-project-btn');
    const closeBtn = document.getElementById('close-project-modal-btn');
    const cancelBtn = document.getElementById('cancel-project-btn');
    const deleteBtn = document.getElementById('delete-project-btn');

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
        vendeur: document.getElementById('project-vendeur'),
        beneficiaire: document.getElementById('project-beneficiaire'),
        locataire: document.getElementById('project-locataire'),
        datePromesse: document.getElementById('project-date-promesse'),
        negociationExterne: document.getElementById('project-negociation-externe'),
        frais: document.getElementById('project-frais'),
        prix: document.getElementById('project-prix'),
        dg: document.getElementById('project-dg'),
        dateDg: document.getElementById('project-date-dg'),
        csPret: document.getElementById('project-cs-pret'),
        dateCsPret: document.getElementById('project-date-cs-pret'),
        dateReiteration: document.getElementById('project-date-reiteration'),
        acte: document.getElementById('project-acte'),
        title: document.getElementById('project-modal-title'),
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

    function renderProjects() {
        if (!tbody) return;
        const q = (searchInput?.value || '').trim().toLowerCase();
        const selectedType = typeFilter?.value || '';
        const filtered = projects.filter(project => {
            const matchesQuery = !q
                || (project.reference || '').toLowerCase().includes(q)
                || (project.affaire || project.name || '').toLowerCase().includes(q)
                || (project.adresse_bien || '').toLowerCase().includes(q)
                || (project.vendeur || '').toLowerCase().includes(q)
                || (project.beneficiaire || '').toLowerCase().includes(q)
                || (project.locataire || '').toLowerCase().includes(q);
            const matchesType = !selectedType || project.type_dossier === selectedType || project.type === selectedType;
            return matchesQuery && matchesType;
        });

        tbody.innerHTML = filtered.map(project => `
            <tr>
                <td><strong>${escapeHtml(project.reference)}</strong></td>
                <td>${escapeHtml(project.affaire || project.name)}</td>
                <td><span class="status-badge">${escapeHtml(project.type_dossier_label || project.type_label)}</span></td>
                <td>${escapeHtml(project.activite_metier_label)}</td>
                <td>${escapeHtml(project.etat_label)}</td>
                <td>${escapeHtml(project.categorie_label || 'Non classé')}</td>
                <td>${money(project.prix)}</td>
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
        `).join('');

        if (emptyState) {
            emptyState.style.display = filtered.length ? 'none' : 'block';
        }
    }

    function setValue(input, value) {
        if (input) input.value = value || '';
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
        setValue(fields.vendeur, project?.vendeur);
        setValue(fields.beneficiaire, project?.beneficiaire);
        setValue(fields.locataire, project?.locataire);
        setValue(fields.datePromesse, project?.date_promesse);
        setValue(fields.negociationExterne, project?.negociation_externe);
        setValue(fields.frais, project?.frais || '0');
        setValue(fields.prix, project?.prix || project?.total_estimated || '0');
        setValue(fields.dg, project?.dg || '0');
        setValue(fields.dateDg, project?.date_dg);
        setValue(fields.csPret, project?.cs_pret);
        setValue(fields.dateCsPret, project?.date_cs_pret);
        setValue(fields.dateReiteration, project?.date_reiteration);
        setValue(fields.acte, project?.acte);
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
        return {
            reference: fields.reference.value,
            affaire: fields.affaire.value,
            type_dossier: fields.type.value,
            activite_metier: fields.activiteMetier.value,
            etat: fields.etat.value,
            categorie_id: fields.categorie.value,
            lot_etage: fields.lotEtage.value,
            adresse_bien: fields.adresseBien.value,
            vendeur: fields.vendeur.value,
            beneficiaire: fields.beneficiaire.value,
            locataire: fields.locataire.value,
            date_promesse: fields.datePromesse.value,
            negociation_externe: fields.negociationExterne.value,
            frais: fields.frais.value || '0',
            prix: fields.prix.value || '0',
            dg: fields.dg.value || '0',
            date_dg: fields.dateDg.value,
            cs_pret: fields.csPret.value,
            date_cs_pret: fields.dateCsPret.value,
            date_reiteration: fields.dateReiteration.value,
            acte: fields.acte.value,
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

    addBtn?.addEventListener('click', () => openProjectModal(null));
    closeBtn?.addEventListener('click', closeProjectModal);
    cancelBtn?.addEventListener('click', closeProjectModal);
    form?.addEventListener('submit', submitProject);
    deleteBtn?.addEventListener('click', deleteProject);
    searchInput?.addEventListener('input', renderProjects);
    typeFilter?.addEventListener('change', renderProjects);

    tbody?.addEventListener('click', event => {
        const btn = event.target.closest('.project-edit-btn');
        if (!btn) return;
        const project = projects.find(item => String(item.id) === String(btn.dataset.projectId));
        if (project) openProjectModal(project);
    });

    modal?.addEventListener('click', event => {
        if (event.target === modal) closeProjectModal();
    });

    renderProjects();
})();
