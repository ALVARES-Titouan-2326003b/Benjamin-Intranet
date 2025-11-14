from django.urls import path
from .views import (
    administratif_view,
    send_reply_view,
    generate_auto_message_view
)

app_name = 'management'

urlpatterns = [
    path('administratif/', administratif_view, name='admin'),

    # API pour l'envoi d'emails
    path('api/send-reply/', send_reply_view, name='send_reply'),
    # API pour la génération automatique de messages
    path('api/generate-message/', generate_auto_message_view, name='generate_message'),
]
