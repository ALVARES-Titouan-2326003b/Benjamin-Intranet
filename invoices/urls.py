from django.urls import path
from .views import (
    FactureListView, FactureDetailView,
    FactureCreateView, FactureUpdateView, ManualInvoiceRemindersView,
    BulkDeleteInvoicesView,
)

from .views_dashboard import DashboardView

app_name = 'invoices'

urlpatterns = [
    path('finance/', FactureListView.as_view(), name='list'),
    path('finance/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('finance/facture/new/', FactureCreateView.as_view(), name='create'),
    path('finance/facture/<str:pk>/edit/', FactureUpdateView.as_view(), name='edit'),
    path('finance/facture/<str:pk>/', FactureDetailView.as_view(), name='detail'),
    path('finance/manual-reminders/', ManualInvoiceRemindersView.as_view(), name='manual_reminders'),
    path('finance/bulk-delete/', BulkDeleteInvoicesView.as_view(), name='bulk_delete'),
]
