import django_filters
from django.db.models import Q
from .models import Facture


class FactureFilter(django_filters.FilterSet):
    fournisseur = django_filters.CharFilter(
        field_name='fournisseur',
        lookup_expr='icontains'
    )
    client = django_filters.CharFilter(method='filter_client')
    dossier = django_filters.CharFilter(method='filter_dossier')
    statut = django_filters.CharFilter(
        field_name='statut',
        lookup_expr='icontains'
    )

    def filter_client(self, queryset, name, value):
        """Filtre par client : recherche dans Entreprise.nom, Particulier nom/prenom, ou ID"""
        return queryset.filter(
            Q(client__entreprise__nom__icontains=value)
            | Q(client__particulier__nom__icontains=value)
            | Q(client__particulier__prenom__icontains=value)
            | Q(client_id__icontains=value)
        )

    def filter_dossier(self, queryset, name, value):
        return queryset.filter(
            Q(dossier__reference__icontains=value)
            | Q(dossier__name__icontains=value)
        )
    min_amount = django_filters.NumberFilter(
        field_name='montant',
        lookup_expr='gte'
    )
    max_amount = django_filters.NumberFilter(
        field_name='montant',
        lookup_expr='lte'
    )

    echeance_min = django_filters.DateFilter(
        field_name='echeance',
        lookup_expr='date__gte',
        label="Échéance après le"
    )
    echeance_max = django_filters.DateFilter(
        field_name='echeance',
        lookup_expr='date__lte',
        label="Échéance avant le"
    )

    class Meta:
        model = Facture
        fields = []
