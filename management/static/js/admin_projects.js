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
        name: document.getElementById('project-name'),
        type: document.getElementById('project-type'),
        total: document.getElementById('project-total-estimated'),
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
                || project.reference.toLowerCase().includes(q)
                || project.name.toLowerCase().includes(q);
            const matchesType = !selectedType || project.type === selectedType;
            return matchesQuery && matchesType;
        });

        tbody.innerHTML = filtered.map(project => `
            <tr>
                <td><strong>${escapeHtml(project.reference)}</strong></td>
                <td>${escapeHtml(project.name)}</td>
                <td><span class="status-badge">${escapeHtml(project.type_label)}</span></td>
                <td>${money(project.total_estimated)}</td>
                <td>${project.activities_count || 0}</td>
                <td>
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

    function openProjectModal(project) {
        clearStatus();
        fields.id.value = project?.id || '';
        fields.reference.value = project?.reference || '';
        fields.name.value = project?.name || '';
        fields.type.value = project?.type || 'client';
        fields.total.value = project?.total_estimated || '0';
        fields.title.innerHTML = project
            ? '<i class="bi bi-pencil-square"></i> Modifier le projet'
            : '<i class="bi bi-kanban"></i> Nouveau projet';
        deleteBtn.style.display = project ? 'inline-flex' : 'none';
        modal.style.display = 'flex';
        fields.reference.focus();
    }

    function closeProjectModal() {
        modal.style.display = 'none';
        form.reset();
        clearStatus();
    }

    async function submitProject(event) {
        event.preventDefault();
        clearStatus();

        const id = fields.id.value;
        const payload = {
            reference: fields.reference.value,
            name: fields.name.value,
            type: fields.type.value,
            total_estimated: fields.total.value || '0',
        };
        const url = id ? `/api/admin-projects/${id}/update/` : '/api/admin-projects/create/';

        try {
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

            const existingIndex = projects.findIndex(project => String(project.id) === String(data.project.id));
            if (existingIndex >= 0) {
                projects[existingIndex] = data.project;
            } else {
                projects.push(data.project);
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
        if (!confirm(`Supprimer le projet ${project?.reference || ''} ?`)) return;

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
