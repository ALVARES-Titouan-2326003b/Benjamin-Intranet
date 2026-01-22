from django.urls import path
from .views import (
    administratif_view,
    send_reply_view,
    generate_auto_message_view,
    get_calendar_activities,
    create_activity_view,
    delete_activity_view
)

app_name = 'management'

urlpatterns = [
    path('administratif/', administratif_view, name='admin'),

    path('api/send-reply/', send_reply_view, name='send_reply'),
    path('api/generate-message/', generate_auto_message_view, name='generate_message'),
    path('api/calendar-activities/', get_calendar_activities, name='calendar_activities'),
    path('api/delete-activity/', delete_activity_view, name='delete_activity'),
    path('api/create-activity/', create_activity_view, name='create_activity'),

]

