import decimal
from json import loads

import requests as req
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View

from ..forms import SubscribeForm
from ..models import Subscription


def debug_pricing():
    pricing = \
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


class Api:
    @staticmethod
    def get(url, *args, **kwargs):
        return Api.__make_request('get', url, *args, **kwargs)

    @staticmethod
    def post(url, data, *args, **kwargs):
        return Api.__make_request('post', url, data, *args, **kwargs)

    @staticmethod
    def __make_request(method, url, data=None, request=None, headers=None):
        try:
            if method == "get":
                r = req.get(url, timeout=2, headers=headers)
            if method == "post":
                r = req.post(url, data=data, timeout=10, headers=headers)
        except (req.Timeout, req.ConnectionError):
            if request:
                messages.warning(request, message="Сервис оформления подписок недоступен.")
            return redirect('partner:account_profile')
        return Api.__raise_for_status(r, request)

    @staticmethod
    def __raise_for_status(r, request=None):
        try:
            r.raise_for_status()
        except req.HTTPError:
            if request:
                messages.warning(request, message="Сервер оформления подписок недоступен.")
            return redirect('partner:account_profile')
        return r.json()


# Затычка api
def get_pricing(request):
    """
    Возвращает
     \n tariffs_json = объект тарифов
     \n quotas = [ {*code*: "", *name*: ""}, ... ] -- список существующих квот
     \n pricing = {...} -- рассчитанная стоимость подписки для переданных в запросе данных
    """

    tariffs_json = Api.get('https://adesk.ru/api/tariffs', request=request)
    if isinstance(tariffs_json, HttpResponseRedirect):
        return tariffs_json

    quotas = tariffs_json['tariffs'][0]['quotas']

    api_data = {
        'client_email': request.POST.get('client_email'),
        'period': request.POST.get('period'),
        'tariff': request.POST.get('tariff'),
        'extra_quotas': {}
    }

    for quota in quotas:
        code = quota['code']
        api_data['extra_quotas'][code] = request.POST.get(code)

    # pricing = Api.post("https://api.adesk.ru/v1/partner/checkout-subscription", data=api_data, request=request)
    pricing = debug_pricing()
    if isinstance(pricing, HttpResponseRedirect):
        return pricing

    pricing['quotas_sum'] = sum([q['price'] for q in pricing['extraQuotas']])

    return tariffs_json, quotas, pricing


class AccountProfileView(LoginRequiredMixin, View):
    template_name = 'partner/account/account_page_profile.html'

    def get(self, request):
        api_down_messages = [m for m in messages.get_messages(request) if m.level == 30]

        if api_down_messages:
            tariffs_json = None
            subscribe_form = SubscribeForm(None, disable_form=True)
        else:
            tariffs_json = Api.get('https://adesk.ru/api/tariffs', request=request)

            if isinstance(tariffs_json, HttpResponseRedirect):
                return tariffs_json

            subscribe_form = SubscribeForm(tariffs_json)

        partner = request.user.partner
        revenue_func = F('cost_value') * F('commission') / 100
        overall = {
            'revenue': Subscription.objects.filter(partner=partner).aggregate(val=Sum(revenue_func)),
            'sales': Subscription.objects.filter(partner=partner).aggregate(Sum('cost_value'))
        }
        return render(request, self.template_name,
                      context={
                          'partner': partner,
                          'overall': overall,
                          'subscribe_form': subscribe_form,
                          'checkout': False,
                          'tariff_json': tariffs_json,
                          'page': {'profile': {'active': 'active'}}
                      })


class AccountHistoryView(LoginRequiredMixin, View):
    template_name = 'partner/account/account_page_history.html'

    def get(self, request):
        partner = request.user.partner
        subs = reversed(Subscription.objects.filter(partner=partner))
        subs_table = {
            'headers': ('Email', 'Стоимость', 'Заработано', 'Процент комиссии', 'Дата оформления', 'Период', 'Тариф'),
            'dataset': subs
        }

        return render(request, self.template_name,
                      context={
                          'partner': partner,
                          'subs_table': subs_table,
                          'page': {'history': {'active': 'active'}}
                      })


class CheckoutView(LoginRequiredMixin, View):
    template_name = 'partner/account/account_page_profile.html'

    def get(self, request):
        return redirect('partner:account_profile')

    def post(self, request):
        r = get_pricing(request)

        if isinstance(r, HttpResponseRedirect):
            return r

        tariffs_json, quotas, pricing = r

        subscribe_form = SubscribeForm(tariffs_json, data=request.POST)
        partner = request.user.partner

        return render(request, self.template_name,
                      context={
                          'partner': partner,
                          'subscribe_form': subscribe_form,
                          'checkout': True,
                          'pricing': pricing,
                          'page': {'profile': {'active': 'active'}}
                      })


class SubscribeView(LoginRequiredMixin, View):
    def post(self, request):
        r = get_pricing(request)

        if isinstance(r, HttpResponseRedirect):
            return r

        tariffs_json, quotas, pricing = r

        sub_form = SubscribeForm(tariffs_json, data=request.POST)
        partner = request.user.partner

        if sub_form.is_valid():

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
            headers = {"Authorization": f"Bearer {settings.BEARER_TOKEN_SUBSCRIBE}"}

            r = {"success": True}
            # r = {"success": False, "message": "err message"}
            # r = Api.post("https://api.adesk.ru/v1/partner/subscription",
            #             data=api_data, request=request, headers=headers)

            if isinstance(r, HttpResponseRedirect):
                return r

            if r['success'] is False:
                messages.error(request, message=r['message'])
                return redirect('partner:account_profile')

            tariff_name = pricing['tariff']['name']

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

            partner.debt += total_price * (1 - partner.commission / 100)
            partner.save(update_fields=['debt'])
            s.save()

            messages.success(request, 'Пользователь успешно подписан.')
            return redirect('partner:account_history')

        messages.error(request, message='Данные указаны неверно.')
        return redirect('partner:account_profile')
