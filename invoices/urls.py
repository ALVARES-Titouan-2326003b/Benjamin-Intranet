from django.urls import path
from .views import (
    FactureListView, FactureDetailView,
    FactureCreateView, FactureUpdateView, ManualInvoiceRemindersView,
    BulkDeleteInvoicesView, CegidExportCreateView, CegidExportDownloadView,
    CegidExportListView, InvoiceAnomaliesView,
    InvoiceReminderSettingsView,
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
    path('exports/cegid/', CegidExportListView.as_view(), name='cegid_exports'),
    path('exports/cegid/new/', CegidExportCreateView.as_view(), name='cegid_export_create'),
    path('exports/cegid/<int:pk>/download/', CegidExportDownloadView.as_view(), name='cegid_export_download'),
    path('anomalies/', InvoiceAnomaliesView.as_view(), name='anomalies'),
]
