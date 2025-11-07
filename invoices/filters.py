import django_filters
from .models import Facture

class FactureFilter(django_filters.FilterSet):
    fournisseur = django_filters.CharFilter(field_name='fournisseur', lookup_expr='icontains')
    client = django_filters.CharFilter(field_name='client__nom', lookup_expr='icontains')
    statut = django_filters.CharFilter(field_name='statut', lookup_expr='icontains')
    min_amount = django_filters.NumberFilter(field_name='montant', lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name='montant', lookup_expr='lte')

    class Meta:
        model = Facture
        fields = []
