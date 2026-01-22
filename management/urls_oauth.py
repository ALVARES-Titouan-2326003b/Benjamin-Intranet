"""
URLs pour le flux OAuth2
"""
from django.urls import path
from . import oauth_views

app_name = 'oauth'

urlpatterns = [
    path('gmail/', oauth_views.initiate_oauth, name='initiate'),

    path('callback/', oauth_views.oauth_callback, name='callback'),

    path('revoke/', oauth_views.revoke_oauth, name='revoke'),

    path('status/', oauth_views.oauth_status, name='status'),
]