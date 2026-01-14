from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'authentication'

urlpatterns = [
    # --- GESTION DES COMPTES ---
    path('gestion-comptes/', views.user_management_view, name='user_management'),
    path('gestion-comptes/inviter/', views.invite_user_view, name='invite_user'),
    path('activate/<str:uidb64>/<str:token>/', views.activate_account_view, name='activate'),

    # --- MOT DE PASSE OUBLIÉ ---
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='authentication/password_reset_form.html',
             email_template_name='authentication/password_reset_email.html',
             success_url=reverse_lazy('authentication:password_reset_done')
         ), 
         name='password_reset'),

    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='authentication/password_reset_done.html'
         ), 
         name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='authentication/password_reset_confirm.html',
             success_url=reverse_lazy('authentication:password_reset_complete')
         ), 
         name='password_reset_confirm'),

    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='authentication/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]
