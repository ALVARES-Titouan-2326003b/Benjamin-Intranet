from django.urls import path
from .views import (
    FactureListView, FactureDetailView,
    FactureCreateView, FactureUpdateView, ManualInvoiceRemindersView,
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
]
