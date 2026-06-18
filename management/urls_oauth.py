"""
URLs pour le flux OAuth2
"""
from django.urls import path
from . import oauth_views

app_name = 'oauth'

urlpatterns = [
    # Le flux Microsoft reste implémenté dans oauth_views pour une réactivation
    # ultérieure, mais il n'est pas publié dans l'interface Gmail-only.
    path('gmail/', oauth_views.initiate_gmail_oauth, name='initiate_gmail'),

    path('callback/', oauth_views.oauth_callback, name='callback'),

    path('revoke/', oauth_views.revoke_oauth, name='revoke'),

    path('status/', oauth_views.oauth_status, name='status'),
]
