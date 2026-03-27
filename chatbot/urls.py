from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('', views.chatbot_interface, name='interface'),
    path('query/', views.chatbot_query, name='query'),
    path('help/', views.chatbot_help, name='help'),
    path('history/', views.chatbot_history, name='history'),
]
