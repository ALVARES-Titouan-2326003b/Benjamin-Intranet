from django.urls import path
from .views import (
    FactureListView, FactureDetailView,
    FactureCreateView, FactureUpdateView,
)

app_name = 'invoices'

urlpatterns = [
    path('finance/', FactureListView.as_view(), name='list'),
    path('finance/facture/new/', FactureCreateView.as_view(), name='create'),
    path('finance/facture/<str:pk>/edit/', FactureUpdateView.as_view(), name='edit'),
    path('finance/facture/<str:pk>/', FactureDetailView.as_view(), name='detail'),
]
