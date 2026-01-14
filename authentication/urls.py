from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('gestion-comptes/', views.user_management_view, name='user_management'),
    path('gestion-comptes/inviter/', views.invite_user_view, name='invite_user'),
    path('activate/<str:uidb64>/<str:token>/', views.activate_account_view, name='activate'),
]
