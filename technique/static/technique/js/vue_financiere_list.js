// Gestion de la sélection multiple pour les projets
document.addEventListener('DOMContentLoaded', function() {
    const selectAllProjects = document.getElementById('selectAllProjects');
    const deleteProjectsBtn = document.getElementById('deleteProjectsBtn');
    const selectedProjectsCount = document.getElementById('selectedProjectsCount');

    if (selectAllProjects) {
        selectAllProjects.addEventListener('change', function() {
            document.querySelectorAll('.project-checkbox').forEach(cb => cb.checked = this.checked);
            updateProjectsButton();
        });

        document.querySelectorAll('.project-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', updateProjectsButton);
        });
    }

    function updateProjectsButton() {
        const count = document.querySelectorAll('.project-checkbox:checked').length;
        deleteProjectsBtn.style.display = count > 0 ? 'inline-block' : 'none';
        selectedProjectsCount.textContent = count;
        if (selectAllProjects) {
            const total = document.querySelectorAll('.project-checkbox').length;
            selectAllProjects.checked = total > 0 && count === total;
        }
    }
});

document.getElementById("showCreateFormBtn").addEventListener("click", function () {
        const form = document.getElementById("createProjectForm");
        form.style.display = (form.style.display === "none") ? "block" : "none";
    });
