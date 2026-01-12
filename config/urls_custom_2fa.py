from django.urls import path
from authentication.views import CustomLoginView

app_name = 'two_factor'

urlpatterns = [
    path('account/login/', CustomLoginView.as_view(), name='login'),

]
