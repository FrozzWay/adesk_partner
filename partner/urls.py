from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import RedirectView

from .views.auth_views import *
from .views.account_views import *

app_name = 'partner'
urlpatterns = [
    path('', RedirectView.as_view(url='login')),
    path('registration/', RegistrationView.as_view(), name='registration'),
    path('registration/success', success_registration, name='success_registration'),
    path('login/', MyLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='partner:login'), name='logout'),

    path('my/', AccountProfileView.as_view(), name='account_profile'),
    path('my/history/', AccountHistoryView.as_view(), name='account_history'),
    path('my/checkout', CheckoutView.as_view(), name='checkout'),
    path('my/checkout/subscribe', SubscribeView.as_view(), name='subscribe'),
]
