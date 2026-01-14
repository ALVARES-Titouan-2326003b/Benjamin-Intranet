"""
URLs pour le flux OAuth2
"""
from django.urls import path
from . import oauth_views

app_name = 'oauth'

urlpatterns = [
    # Initier le flux OAuth (redirection vers Microsoft)
    path('microsoft/', oauth_views.initiate_oauth, name='initiate'),

    # Callback OAuth (retour depuis Microsoft)
    path('callback/', oauth_views.oauth_callback, name='callback'),

    # Révoquer l'accès OAuth
    path('revoke/', oauth_views.revoke_oauth, name='revoke'),

    # Vérifier le statut OAuth
    path('status/', oauth_views.oauth_status, name='status'),
]