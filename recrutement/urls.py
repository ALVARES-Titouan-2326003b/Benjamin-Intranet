# recrutement/urls.py
from django.urls import path
from . import views

app_name = "recrutement"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("fiche/nouvelle/", views.fiche_create, name="fiche_create"),
    path("fiche/<int:pk>/", views.fiche_detail, name="fiche_detail"),
    path("fiche/<int:pk>/upload-cv/", views.upload_cv, name="upload_cv"),
    path("fiches/bulk-delete/", views.bulk_delete_fiches, name="bulk_delete_fiches"),
    path("candidatures/bulk-delete/", views.bulk_delete_candidatures, name="bulk_delete_candidatures"),
]
 