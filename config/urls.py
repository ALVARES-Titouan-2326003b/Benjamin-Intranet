from django.contrib import admin

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from management.views import administratif_view, send_reply_view, generate_auto_message_view, get_calendar_activities
from technique import views as technique_views
from home.views import dashboard_view, global_search

urlpatterns = [
    path('admin/', admin.site.urls),
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'img/favicon.png', permanent=True)),
    path('', dashboard_view, name='home'),
    path('recherche/', global_search, name='global_search'),
    path('administratif/', administratif_view, name='admin_view'),
    
    # On met ceci AVANT les autres pour être sûr que les URLs de login sont prioritaires
    path('', include('config.urls_custom_2fa')),
    # API pour l'envoi d'emails
    path('api/send-reply/', send_reply_view, name='send_reply'),
    # API pour la génération automatique de messages
    path('api/generate-message/', generate_auto_message_view, name='generate_message'),
    # API pour le calendrier
    path('api/calendar-activities/', get_calendar_activities, name='calendar_activities'),

    # LIGNES RESTAURÉES POUR LOGOUT
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('oauth/', include('management.urls_oauth')),
    path('chatbot/', include('chatbot.urls')),
    path('finance/', include('invoices.urls')),
    path('auth/', include('authentication.urls')),
    path('gestion-des-candidatures/', include('recrutement.urls')),
    path('pole-technique/documents/', include('technique.urls')),

    path('signatures/', include('signatures.urls')),
    # Module financier partie technique
    path(
    "pole-technique/vue-financiere/",
    technique_views.financial_overview,
    name="technique_financial_overview",
    ),
    path(
    "pole-technique/vue-financiere/<int:pk>/",
    technique_views.financial_project_detail,
    name="technique_financial_project_detail",
    ),
    path(
    "pole-technique/vue-financiere/<int:pk>/pdf/",
    technique_views.financial_project_pdf,
    name="technique_financial_project_pdf",
    ),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
