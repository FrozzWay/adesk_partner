import decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .forms import PartnerRegistrationForm, CustomAuthForm, SubscribeForm
from django.contrib.auth.views import LoginView
from requests import get as api_get
from requests import post as api_post

from json import loads

from .models import Partner, Subscription


def get_tariffs():
    """
    Возвращает список тарифов и квот с их кодами и названиями.
     \n tariffs_choices = [ (*code*, *name*), ... ]
     \n quotas = [ {*code*: "", *name*: ""}, ... ]
    """
    tariff_json = api_get('https://adesk.ru/api/tariffs').json()
    tariffs_choices = [(obj['code'], obj['name']) for obj in tariff_json['tariffs']]
    quotas = tariff_json['tariffs'][0]['quotas']

    return tariffs_choices, quotas, tariff_json


# Затычка api
def retrieve_data_from_request(request):
    """
    Возвращает
     \n tariffs_choices = [ (*code*, *name*), ... ]  -- список существующих тарифов для заполнения choices
     \n quotas = [ {*code*: "", *name*: ""}, ... ] -- список существующих квот
     \n pricing = {...} -- рассчитанная стоимость подписки для переданных в запросе данных
    """
    tariffs_choices, quotas, tariffs_json = get_tariffs()

    api_data = {
        'client_email': request.POST.get('client_email'),
        'period': request.POST.get('period'),
        'tariff': request.POST.get('tariff'),
        'extra_quotas': {}
    }

    for quota in quotas:
        code = quota['code']
        api_data['extra_quotas'][code] = request.POST.get(code)

    # pricing = api_post("https://api.adesk.ru/v1/partner/checkout-subscription", data=api_data).json()
    pricing = debug_pricing()

    pricing['quotas_sum'] = sum([q['price'] for q in pricing['extraQuotas']])

    return tariffs_choices, quotas, pricing


@require_http_methods(["GET", "POST"])
def registration(request):

    if request.method == 'POST':

        form = PartnerRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            request.session['pp_redarekt'] = True
            return redirect('myapp:success_registration')

    else:
        form = PartnerRegistrationForm()

    return render(request, template_name='myapp/auth/registration.html', context={'form': form})


def success_registration(request):
    if 'pp_redarekt' in request.session:
        del request.session['pp_redarekt']
        return render(request, template_name='myapp/auth/success_registration.html')

    return redirect('myapp:registration')


class MyLoginView(LoginView):
    template_name = 'myapp/auth/login.html'
    next_page = 'myapp:account_profile'
    redirect_authenticated_user = True
    authentication_form = CustomAuthForm


@login_required(login_url='myapp:login')
def account_profile(request):
    tariffs_choices, quotas, tariffs_json = get_tariffs()

    subscribe_form = SubscribeForm(tariffs_choices, quotas)

    partner = Partner.objects.get(user__email=request.user.email)
    revenue_func = F('cost_value')*F('commission')/100
    overall = {
        'revenue': Subscription.objects.filter(partner=partner).aggregate(val=Sum(revenue_func)),
        'sales': Subscription.objects.filter(partner=partner).aggregate(Sum('cost_value'))
    }

    return render(request, template_name='myapp/account/account_page_profile.html',
                  context={
                      'partner': partner,
                      'overall': overall,
                      'subscribe_form': subscribe_form,
                      'checkout': False,
                      'tariff_json': tariffs_json,
                      'page': {'profile': {'active': 'active'}}
                  })


@login_required(login_url='myapp:login')
def account_history(request):
    partner = Partner.objects.get(user__email=request.user.email)
    subs = reversed(Subscription.objects.filter(partner=partner))
    subs_table = {
        'headers': ('Email', 'Стоимость', 'Заработано', 'Процент комиссии', 'Дата оформления', 'Период', 'Тариф'),
        'dataset': subs
    }

    return render(request, template_name='myapp/account/account_page_history.html',
                  context={
                      'partner': partner,
                      'subs_table': subs_table,
                      'page': {'history': {'active': 'active'}}
                  })


def debug_pricing():
    pricing =\
    '''
    {
    "totalPrice":30990.0,
    "period":12,
    "tariff":{
      "code":"business",
      "name":"Бизнес",
      "price":24990.0
    },
    "options":[],
    "quotas":[],
    "extraOptions":[],
    "extraQuotas":[
      {
        "code":"users",
        "name":"Пользователи",
        "unitPrice":100.0,
        "price":1200.0,
        "quantity":1
      },
      {
        "code":"legal_entities",
        "name":"Юр. лица",
        "unitPrice":200.0,
        "price":4800.0,
        "quantity":2
      }
    ]
    }
    '''
    return loads(pricing)


@login_required(login_url='myapp:login')
def checkout(request):
    if request.method == 'GET':
        return redirect('myapp:account_profile')

    tariffs_choices, quotas, pricing = retrieve_data_from_request(request)

    subscribe_form = SubscribeForm(tariffs_choices, quotas, request.POST)

    partner = Partner.objects.get(user__email=request.user.email)

    return render(request, template_name='myapp/account/account_page_profile.html',
                  context={
                      'partner': partner,
                      'subscribe_form': subscribe_form,
                      'checkout': True,
                      'pricing': pricing,
                      'page': {'profile': {'active': 'active'}}
                  })


# Затычка api
@require_http_methods(["POST"])
@login_required(login_url='myapp:login')
def subscribe(request):
    tariffs_choices, quotas, pricing = retrieve_data_from_request(request)

    sub_form = SubscribeForm(tariffs_choices, quotas, request.POST)

    if sub_form.is_valid():
        partner = Partner.objects.get(user__email=request.user.email)

        quotas_codes = [quota['code'] for quota in quotas]

        quotas = dict()

        for field in sub_form.fields:
            if field in quotas_codes:
                quotas[field] = sub_form.cleaned_data[field]

        api_data = {
            'client_email': sub_form.cleaned_data['client_email'],
            'period': sub_form.cleaned_data['period'],
            'tariff': sub_form.cleaned_data['tariff'],
            'extra_quotas': quotas
        }

        # r = api_post("https://api.adesk.ru/v1/partner/subscription", data=api_data).json()
        r = {"success": True}

        if r['success'] is False:
            messages.error(request, message=r['message'])
            return redirect('myapp:account_profile')

        tariff_code = sub_form.cleaned_data['tariff']
        tariff_name = dict(tariffs_choices)[tariff_code]

        s = Subscription(
            partner=partner,
            email=sub_form.cleaned_data['client_email'],
            cost_value=pricing['totalPrice'],
            commission=partner.commission,
            reg_date=timezone.now(),
            period=sub_form.cleaned_data['period'],
            tariff=tariff_name,
            quotas=quotas
        )

        total_price = decimal.Decimal(pricing['totalPrice'])

        partner.debt = partner.debt + total_price - total_price * partner.commission / 100
        partner.save(update_fields=['debt'])
        s.save()

        messages.success(request, 'Profile details updated.')
        return redirect('myapp:account_history')

    messages.error(request, message='Данные указаны неверно.')
    return redirect('myapp:account_profile')
