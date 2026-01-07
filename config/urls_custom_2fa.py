from django.urls import path, include
from two_factor.views import LoginView

app_name = 'two_factor'

urlpatterns = [
    path('account/login/', LoginView.as_view(), name='login'),

]
