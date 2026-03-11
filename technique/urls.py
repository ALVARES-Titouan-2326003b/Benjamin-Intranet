from django.urls import path
from . import views

app_name = "technique"

urlpatterns = [
    path("", views.documents_list, name="documents_list"),
    path("upload/", views.documents_upload, name="documents_upload"),
    path("<int:pk>/", views.documents_detail, name="documents_detail"),
    path("<int:pk>/pdf/", views.document_resume_pdf, name="document_resume_pdf"),
    path("bulk-delete/", views.bulk_delete_documents, name="bulk_delete_documents"),
    path("documents/<int:pk>/edit/", views.documents_update, name="documents_update"),

    path("finance/", views.financial_overview, name="technique_financial_overview"),
    path("finance/bulk-delete/", views.bulk_delete_projects, name="bulk_delete_projects"),
    path("finance/<int:pk>/", views.financial_project_detail, name="technique_financial_project_detail"),
    path("finance/<int:pk>/pdf/", views.financial_project_pdf, name="technique_financial_project_pdf"),
    path("finance/<int:pk>/csv/", views.financial_project_csv, name="technique_financial_project_csv"),
    path("finance/<int:pk>/excel/", views.financial_project_excel, name="technique_financial_project_excel"),
    path("finance/<int:pk>/expenses/create/", views.project_expense_create, name="technique_project_expense_create"),
    path("finance/expenses/<int:expense_pk>/update/", views.project_expense_update, name="technique_project_expense_update"),
    path("finance/expenses/<int:expense_pk>/delete/", views.project_expense_delete, name="technique_project_expense_delete"),
]