from django.urls import path
from . import views

app_name = "technique"

urlpatterns = [
    # Documents
    path("documents/",views.documents_list,name="documents_list"),
    path("documents/upload/", views.documents_upload,name="documents_upload"),
    path("documents/<int:pk>/",views.documents_detail,name="documents_detail"),
    path("documents/<int:pk>/pdf/",views.document_resume_pdf,name="document_resume_pdf"),
    path("documents/bulk-delete/",views.bulk_delete_documents,name="bulk_delete_documents"),
    path("documents/<int:pk>/edit/",views.documents_update,name="documents_update"),

    # Emails
    path("email/",views.email_list,name="email_list"),
    path("email/import/",views.email_import_gmail,name="email_import"),
    path("email/classify-bulk/",views.email_ai_classify_bulk,   name="email_classify_bulk"),
    path("email/<int:pk>/",views.email_detail,name="mail_detail"),
    path("email/<int:pk>/assign/",views.mail_assign_project,      name="mail_assign_project"),
    path("email/<int:pk>/classify/",     views.email_ai_classify,        name="email_classify"),

    # Dossiers techniques
    path("dossiers/",                                         views.financial_overview,                  name="dossiers_list"),
    path("dossiers/bulk-delete/",                             views.bulk_delete_projects,                name="dossiers_bulk_delete"),
    path("dossiers/<int:pk>/",                                views.financial_project_detail,            name="dossier_detail"),
    path("dossiers/<int:pk>/pdf/",                            views.financial_project_pdf,               name="dossier_budget_pdf"),
    path("dossiers/<int:pk>/csv/",                            views.financial_project_csv,               name="dossier_budget_csv"),
    path("dossiers/<int:pk>/excel/",                          views.financial_project_excel,             name="dossier_budget_excel"),
    path("dossiers/<int:pk>/expenses/create/",                views.project_expense_create,              name="dossier_expense_create"),
    path("dossiers/expenses/<int:expense_pk>/update/",        views.project_expense_update,              name="dossier_expense_update"),
    path("dossiers/expenses/<int:expense_pk>/delete/",        views.project_expense_delete,              name="dossier_expense_delete"),
    path("dossiers/<int:pk>/actions/create/",                 views.project_action_create,               name="dossier_action_create"),
    path("dossiers/actions/<int:action_pk>/update/",          views.project_action_update,               name="dossier_action_update"),
    path("dossiers/actions/<int:action_pk>/delete/",          views.project_action_delete,               name="dossier_action_delete"),
    path("dossiers/<int:pk>/dates-cles/create/",              views.project_key_date_create,             name="dossier_key_date_create"),
    path("dossiers/dates-cles/<int:key_date_pk>/update/",     views.project_key_date_update,             name="dossier_key_date_update"),
    path("dossiers/dates-cles/<int:key_date_pk>/delete/",     views.project_key_date_delete,             name="dossier_key_date_delete"),

    # Vue financière : anciennes URLs conservées pour compatibilité
    path("vue-financiere/",                                    views.financial_overview,                  name="technique_financial_overview"),
    path("vue-financiere/bulk-delete/",                        views.bulk_delete_projects,                name="bulk_delete_projects"),
    path("vue-financiere/<int:pk>/",                           views.financial_project_detail,            name="technique_financial_project_detail"),
    path("vue-financiere/<int:pk>/pdf/",                       views.financial_project_pdf,               name="technique_financial_project_pdf"),
    path("vue-financiere/<int:pk>/csv/",                       views.financial_project_csv,               name="technique_financial_project_csv"),
    path("vue-financiere/<int:pk>/excel/",                     views.financial_project_excel,             name="technique_financial_project_excel"),
    path("vue-financiere/<int:pk>/expenses/create/",           views.project_expense_create,              name="technique_project_expense_create"),
    path("vue-financiere/expenses/<int:expense_pk>/update/",   views.project_expense_update,              name="technique_project_expense_update"),
    path("vue-financiere/expenses/<int:expense_pk>/delete/",   views.project_expense_delete,              name="technique_project_expense_delete"),
]
