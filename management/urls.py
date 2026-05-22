from django.urls import path
from .views import (
    admin_projects_view,
    administratif_view,
    send_reply_view,
    generate_auto_message_view,
    get_calendar_activities,
    create_activity_view,
    delete_activity_view,
    get_calendar_activities_week,
    update_activity_view,
    create_project_view,
    update_project_view,
    delete_project_view,
)

app_name = 'management'

urlpatterns = [
    path('administratif/', administratif_view, name='admin'),
    path('administratif/projets/', admin_projects_view, name='admin_projects'),

    path('api/send-reply/', send_reply_view, name='send_reply'),
    path('api/generate-message/', generate_auto_message_view, name='generate_message'),
    path('api/calendar-activities/', get_calendar_activities, name='calendar_activities'),
    path('api/delete-activity/', delete_activity_view, name='delete_activity'),
    path('api/create-activity/', create_activity_view, name='create_activity'),
    path('api/calendar-activities-week/', get_calendar_activities_week, name='calendar_activities_week'),
    path('api/update-activity/<str:activity_id>/', update_activity_view, name='update_activity'),
    path('api/admin-projects/create/', create_project_view, name='admin_project_create'),
    path('api/admin-projects/<int:project_id>/update/', update_project_view, name='admin_project_update'),
    path('api/admin-projects/<int:project_id>/delete/', delete_project_view, name='admin_project_delete'),
]
