(function () {
  function bindCompanyProjectFilter(companySelect, projectSelect, options) {
    if (!companySelect || !projectSelect || projectSelect.dataset.companyFilterBound === 'true') {
      return null;
    }

    const settings = Object.assign({
      allowEmptyProject: false,
      emptyWhenCompany: '-- Sélectionner un dossier --',
      emptyWithoutCompany: '-- Sélectionnez d’abord une société --',
    }, options || {});
    const projectOptions = Array.from(projectSelect.options)
      .filter(option => option.value)
      .map(option => option.cloneNode(true));

    function refresh(preferredProjectId) {
      const companyId = String(companySelect.value || '');
      const currentProjectId = String(
        preferredProjectId === undefined ? projectSelect.value : preferredProjectId || ''
      );
      const emptyOption = document.createElement('option');
      emptyOption.value = '';
      emptyOption.textContent = companyId
        ? settings.emptyWhenCompany
        : settings.emptyWithoutCompany;
      emptyOption.disabled = !settings.allowEmptyProject && Boolean(companyId);

      const available = companyId
        ? projectOptions.filter(option => option.dataset.companyId === companyId)
        : [];
      projectSelect.replaceChildren(
        emptyOption,
        ...available.map(option => option.cloneNode(true))
      );

      if (available.some(option => String(option.value) === currentProjectId)) {
        projectSelect.value = currentProjectId;
      } else {
        projectSelect.value = '';
      }
      projectSelect.disabled = !companyId;
      projectSelect.dispatchEvent(new CustomEvent('company-project-filtered'));
    }

    companySelect.addEventListener('change', function () {
      refresh('');
    });
    projectSelect.dataset.companyFilterBound = 'true';
    refresh(projectSelect.value);

    return { refresh };
  }

  window.bindCompanyProjectFilter = bindCompanyProjectFilter;
})();
