from django.urls import path
from . import views

app_name = "signatures"

urlpatterns = [
    path("", views.document_list, name="document_list"),
    path("upload/", views.upload_document, name="upload_document"),
    path("<int:pk>/", views.document_detail, name="document_detail"),
    path("<int:pk>/envoyer/", views.envoyer_signature, name="envoyer_signature"),
    path("ma-signature/", views.ma_signature, name="ma_signature"),
    path("tampon/", views.tampon_edit, name="tampon_edit"),
    path("<int:pk>/placer/", views.placer_signature, name="placer_signature"),
    path("<int:pk>/placement/", views.config_placement, name="config_placement"),
    path(
        "approbation/<str:token>/",
        views.signature_approval,
        name="signature_approval",
    ),
    path("ceo/", views.ceo_dashboard, name="ceo_dashboard"),
    path("bulk-delete/", views.bulk_delete_documents, name="bulk_delete"),
]
