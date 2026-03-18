// Gestion de la sélection multiple pour les documents
document.addEventListener('DOMContentLoaded', function() {
    const selectAllDocs = document.getElementById('selectAllDocs');
    const deleteDocsBtn = document.getElementById('deleteDocsBtn');
    const selectedDocsCount = document.getElementById('selectedDocsCount');

    if (selectAllDocs) {
        selectAllDocs.addEventListener('change', function() {
            document.querySelectorAll('.doc-checkbox').forEach(cb => cb.checked = this.checked);
            updateDocsButton();
        });

        document.querySelectorAll('.doc-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', updateDocsButton);
        });
    }

    function updateDocsButton() {
        const count = document.querySelectorAll('.doc-checkbox:checked').length;
        deleteDocsBtn.style.display = count > 0 ? 'inline-block' : 'none';
        selectedDocsCount.textContent = count;
        if (selectAllDocs) {
            const total = document.querySelectorAll('.doc-checkbox').length;
            selectAllDocs.checked = total > 0 && count === total;
        }
    }
});