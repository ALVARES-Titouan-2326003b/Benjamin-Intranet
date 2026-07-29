from django.urls import path
from django.views.generic import RedirectView

from .views import (
    BulkDeleteInvoicesView,
    FactureCreateView,
    FactureDetailView,
    FactureListView,
    FactureUpdateView,
    InvoiceAnomaliesView,
)
from .views_dashboard import DashboardView


app_name = "invoices"

urlpatterns = [
    path("", FactureListView.as_view(), name="list"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("facture/new/", FactureCreateView.as_view(), name="create"),
    path("facture/<str:pk>/edit/", FactureUpdateView.as_view(), name="edit"),
    path("facture/<str:pk>/", FactureDetailView.as_view(), name="detail"),
    path("bulk-delete/", BulkDeleteInvoicesView.as_view(), name="bulk_delete"),
    path("anomalies/", InvoiceAnomaliesView.as_view(), name="anomalies"),
    path(
        "societes/",
        RedirectView.as_view(pattern_name="admin_societes", permanent=False),
        name="societes",
    ),
    path(
        "societes/<int:pk>/details/",
        RedirectView.as_view(pattern_name="admin_societe_detail", permanent=False),
        name="societe_detail",
    ),
    path(
        "societes/<int:pk>/",
        RedirectView.as_view(pattern_name="admin_societe_update", permanent=False),
        name="societe_update",
    ),
]
