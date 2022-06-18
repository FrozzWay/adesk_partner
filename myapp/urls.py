from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'myapp'
urlpatterns = [
    path('', RedirectView.as_view(url='login')),
    path('registration/', views.registration, name='registration'),
    path('registration/success', views.success_registration, name='success_registration'),
    path('login/', views.MyLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='myapp:login'), name='logout'),

    path('my/', views.account_profile, name='account_profile'),
    path('my/history/', views.account_history, name='account_history'),
    path('my/checkout', views.checkout, name='checkout'),
    path('my/checkout/subscribe', views.subscribe, name='subscribe'),
]
