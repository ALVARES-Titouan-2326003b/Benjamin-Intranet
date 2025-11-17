from django.urls import path
from . import views

app_name = "technique"

urlpatterns = [
    path("", views.documents_list, name="documents_list"),
    path("upload/", views.documents_upload, name="documents_upload"),
    path("<int:pk>/", views.documents_detail, name="documents_detail"),
    path("<int:pk>/pdf/", views.document_resume_pdf, name="document_resume_pdf"),
]
