from django.urls import path
from . import views

app_name = "technique"

urlpatterns = [
    path("documents/", views.documents_list, name="documents_list"),
    path("documents/upload/", views.documents_upload, name="documents_upload"),
    path("documents/<int:pk>/", views.documents_detail, name="documents_detail"),
    path("documents/<int:pk>/pdf/", views.document_resume_pdf, name="document_resume_pdf"),
    path("documents/bulk-delete/", views.bulk_delete_documents, name="bulk_delete_documents"),
    path("documents/<int:pk>/edit/", views.documents_update, name="documents_update"),

    path("email/", views.email_list, name="email_list"),

    path("vue-financiere/", views.financial_overview, name="technique_financial_overview"),
    path("vue-financiere/bulk-delete/", views.bulk_delete_projects, name="bulk_delete_projects"),
    path("vue-financiere/<int:pk>/", views.financial_project_detail, name="technique_financial_project_detail"),
    path("vue-financiere/<int:pk>/pdf/", views.financial_project_pdf, name="technique_financial_project_pdf"),
    path("vue-financiere/<int:pk>/csv/", views.financial_project_csv, name="technique_financial_project_csv"),
    path("vue-financiere/<int:pk>/excel/", views.financial_project_excel, name="technique_financial_project_excel"),
    path("vue-financiere/<int:pk>/expenses/create/", views.project_expense_create, name="technique_project_expense_create"),
    path("vue-financiere/expenses/<int:expense_pk>/update/", views.project_expense_update, name="technique_project_expense_update"),
    path("vue-financiere/expenses/<int:expense_pk>/delete/", views.project_expense_delete, name="technique_project_expense_delete"),
]