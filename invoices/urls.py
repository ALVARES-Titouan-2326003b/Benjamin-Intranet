from django.urls import path
from .viewsFin import (
    FactureListView, FactureDetailView,
    FactureCreateView, FactureUpdateView,
)
from .viewsAdm import (
    administratif_view,
    send_reply_view,
    generate_auto_message_view,  # Nouvelle import
)

app_name = 'invoices'

urlpatterns = [
    path('finance/', FactureListView.as_view(), name='list'),
    path('finance/facture/new/', FactureCreateView.as_view(), name='create'),
    path('finance/facture/<str:pk>/edit/', FactureUpdateView.as_view(), name='edit'),
    path('finance/facture/<str:pk>/', FactureDetailView.as_view(), name='detail'),
    path('administratif/', administratif_view, name='admin'),

    # API pour l'envoi d'emails
    path('api/send-reply/', send_reply_view, name='send_reply'),

    # API pour la génération automatique de messages
    path('api/generate-message/', generate_auto_message_view, name='generate_message'),
]