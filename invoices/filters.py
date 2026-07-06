import django_filters
from django.db.models import Q
from .models import Facture


class FactureFilter(django_filters.FilterSet):
    numero_facture = django_filters.CharFilter(
        field_name='numero_facture',
        lookup_expr='icontains'
    )
    societe = django_filters.CharFilter(
        field_name='societe',
        lookup_expr='icontains'
    )
    affaire = django_filters.CharFilter(
        field_name='affaire',
        lookup_expr='icontains'
    )
    fournisseur = django_filters.CharFilter(method='filter_fournisseur')
    dossier = django_filters.CharFilter(method='filter_dossier')
    statut = django_filters.CharFilter(
        field_name='statut',
        lookup_expr='exact'
    )
    service = django_filters.CharFilter(
        field_name='service',
        lookup_expr='exact'
    )
    priorite = django_filters.CharFilter(
        field_name='priorite',
        lookup_expr='exact'
    )

    def filter_fournisseur(self, queryset, name, value):
        return queryset.filter(
            Q(fournisseur__nom__icontains=value)
            | Q(fournisseur_id__icontains=value)
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

    date_facture_min = django_filters.DateFilter(
        field_name='date_facture',
        lookup_expr='gte',
        label="Date de facture après le"
    )
    date_facture_max = django_filters.DateFilter(
        field_name='date_facture',
        lookup_expr='lte',
        label="Date de facture avant le"
    )

    class Meta:
        model = Facture
        fields = []
