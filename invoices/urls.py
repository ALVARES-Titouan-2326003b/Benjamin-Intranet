from django.urls import path
from .views import (
    FactureListView, FactureDetailView,
    FactureCreateView, FactureUpdateView, ManualInvoiceRemindersView,
    BulkDeleteInvoicesView, InvoiceAnomaliesView,
    InvoiceReminderSettingsView,
    societe_list_create, societe_update,
)

from .views_dashboard import DashboardView

app_name = 'invoices'

urlpatterns = [
    path('', FactureListView.as_view(), name='list'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('facture/new/', FactureCreateView.as_view(), name='create'),
    path('facture/<str:pk>/edit/', FactureUpdateView.as_view(), name='edit'),
    path('facture/<str:pk>/', FactureDetailView.as_view(), name='detail'),
    path('manual-reminders/', ManualInvoiceRemindersView.as_view(), name='manual_reminders'),
    path('reminder-settings/', InvoiceReminderSettingsView.as_view(), name='reminder_settings'),
    path('bulk-delete/', BulkDeleteInvoicesView.as_view(), name='bulk_delete'),
    path('anomalies/', InvoiceAnomaliesView.as_view(), name='anomalies'),
    path('societes/', societe_list_create, name='societes'),
    path('societes/<int:pk>/', societe_update, name='societe_update'),
]
