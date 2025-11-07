# urls.py
from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Authentification (désactivée pour le moment)
    # path('', views.login_view, name='login'),
    # path('login/', views.login_view, name='login'),

    # Pages des pôles
    path('', views.administratif_view, name='admin'),  # Page d'accueil = admin
    path('administratif/', views.administratif_view, name='admin'),
    path('finance/', views.finance_view, name='finance'),
    path('developpement/', views.developpement_view, name='developpement'),
    path('technique/', views.technique_view, name='technique'),

    # API pour l'envoi d'emails
    path('api/send-reply/', views.send_reply_view, name='send_reply'),
]