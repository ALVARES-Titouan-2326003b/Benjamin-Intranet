from django import forms


class CompanyProjectSelect(forms.Select):
    """Expose la société du dossier pour permettre un filtrage côté navigateur."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        project = getattr(value, "instance", None)
        if project is not None:
            option["attrs"]["data-company-id"] = str(project.societe_id)
            option["attrs"]["data-societe-id"] = str(project.societe_id)
        return option
