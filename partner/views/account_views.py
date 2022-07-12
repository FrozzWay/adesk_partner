import decimal
import json
from json import loads

import requests as req
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Sum, F
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View

from ..forms import SubscribeForm
from ..models import Subscription, Partner


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
    def __make_request(method, url, data=None, request=None, headers=None, auth=None):
        try:
            if method == "get":
                r = req.get(url, timeout=2, headers=headers, auth=auth, verify=False)
            if method == "post":
                r = req.post(url, data=data, timeout=10, headers=headers, auth=auth, verify=False)
        except (req.Timeout, req.ConnectionError) as e:
            if request:
                messages.warning(request, message="Сервис оформления подписок недоступен.")
            raise ConnectionError
        return Api.__raise_for_status(r, request)

    @staticmethod
    def __raise_for_status(r, request=None):
        try:
            r.raise_for_status()
        except req.HTTPError:
            if request:
                messages.warning(request, message="Сервер оформления подписок недоступен.")
            raise ConnectionError
        return r.json()


# Затычка api
def get_pricing(request):
    """
    Возвращает
     \n tariffs_json = объект тарифов
     \n tariff_obj -- объект тарифа, указанного в request
     \n extra_quotas - extra квоты {code: value}
     \n pricing = {...} -- рассчитанная стоимость подписки
     \n sub_form
    """

    tariffs_json = Api.get('https://adesk.ru/api/tariffs', request=request)

    sub_form = SubscribeForm(tariffs_json, data=request.POST)

    if sub_form.is_valid():

        tariff_code = sub_form.cleaned_data['tariff']
        tariff_obj = next(filter(lambda t: t['code'] == tariff_code, tariffs_json['tariffs']))

        api_data = {
            'client_email': sub_form.cleaned_data['client_email'],
            'period': sub_form.cleaned_data['period'],
            'tariff': tariff_code,
            'extra_quotas': {},
            'extra_options': "[]",
        }

        for quota in tariff_obj['quotas']:
            code = quota['code']
            default_quota_value = quota['quantity']
            extra_value = sub_form.cleaned_data[code] - default_quota_value
            if extra_value > 0:
                api_data['extra_quotas'][code] = extra_value

        api_data['extra_quotas'] = json.dumps(api_data['extra_quotas'])
        headers = {"App-Token": settings.APP_TOKEN_SUBSCRIBE}

        r = Api.post(settings.CHECKOUT_LINK, data=api_data, request=request, auth=settings.DEV_AUTH, headers=headers)

        if r['success'] is False:
            messages.error(request, message=r['message'])
            raise ValidationError(r['message'])

        pricing = r['pricing']
        pricing['quotas_sum'] = sum([q['price'] for q in pricing['extraQuotas']])

        return tariffs_json, tariff_obj, api_data['extra_quotas'], pricing, sub_form

    messages.error(request, message='Данные указаны неверно.')
    raise ValidationError("")


def get_overall(partner):
    revenue_func = F('cost_value') * F('commission') / 100
    return {
        'revenue': Subscription.objects.filter(partner=partner).aggregate(val=Sum(revenue_func)),
        'sales': Subscription.objects.filter(partner=partner).aggregate(Sum('cost_value'))
    }


class AccountProfileView(LoginRequiredMixin, View):
    template_name = 'partner/account/account_page_profile.html'

    def get(self, request):
        try:
            partner = request.user.partner
        except Partner.DoesNotExist:
            return redirect('/admin')

        api_down_messages = [m for m in messages.get_messages(request) if m.level == 30]

        if api_down_messages:
            tariffs_json = None
            subscribe_form = SubscribeForm(None, disable_form=True)
        else:
            try:
                tariffs_json = Api.get('https://adesk.ru/api/tariffs', request=request)
            except ConnectionError:
                return redirect('partner:account_profile')
            subscribe_form = SubscribeForm(tariffs_json)

        overall = get_overall(partner)
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
        try:
            r = get_pricing(request)
        except (ConnectionError, ValidationError):
            return redirect('partner:account_profile')

        tariffs_json, tariff_obj, extra_quotas, pricing, sub_form = r

        partner = request.user.partner
        overall = get_overall(partner)

        return render(request, self.template_name,
                      context={
                          'partner': partner,
                          'overall': overall,
                          'subscribe_form': sub_form,
                          'checkout': True,
                          'pricing': pricing,
                          'page': {'profile': {'active': 'active'}}
                      })


class SubscribeView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            r = get_pricing(request)
        except (ConnectionError, ValidationError):
            return redirect('partner:account_profile')

        tariffs_json, tariff_obj, extra_quotas, pricing, sub_form = r

        quotas_all = []

        for quota in tariff_obj['quotas']:
            code = quota['code']
            obj = {
                "code": code,
                "name": quota['name'],
                "value": sub_form.cleaned_data[code]
            }
            quotas_all.append(obj)

        partner = request.user.partner

        total_price = decimal.Decimal(pricing['totalPrice'])
        partner_commission = total_price * partner.commission / 100

        api_data = {
            'client_email': sub_form.cleaned_data['client_email'],
            'partner_email': request.user.email,
            'partner_commission': partner_commission,
            'period': sub_form.cleaned_data['period'],
            'tariff': sub_form.cleaned_data['tariff'],
            'extra_quotas': extra_quotas,
            'extra_options': "[]",
        }
        headers = {"App-Token": f"{settings.APP_TOKEN_SUBSCRIBE}"}

        try:
            r = Api.post(settings.SUBSCRIBE_LINK, data=api_data, request=request, headers=headers,
                         auth=settings.DEV_AUTH)
        except ConnectionError:
            return redirect('partner:account_profile')

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
            quotas=quotas_all
        )

        partner.debt += total_price * (1 - partner.commission / 100)
        partner.save(update_fields=['debt'])
        s.save()

        messages.success(request, 'Пользователь успешно подписан.')
        return redirect('partner:account_history')
