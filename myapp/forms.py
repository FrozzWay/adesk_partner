from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.forms import TextInput, PasswordInput
from django.utils import timezone
from django.core.exceptions import ValidationError
from requests import get as api_get

from .models import User, Partner


class PartnerRegistrationForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = Partner
        fields = ('first_name', 'last_name', 'company_name', 'INN', 'phone_number')
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'company_name': 'Наименование компании',
            'INN': 'ИНН',
            'phone_number': 'Номер телефона'
        }
        help_texts = {
            'company_name': 'Укажите, если имеется'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['INN'].widget.attrs.update({'placeholder': '7448963440'})
        self.fields['email'].widget.attrs.update({'placeholder': 'example@example.com'})
        self.fields['phone_number'].widget.attrs.update({'placeholder': '+7 ( 900 ) 123-45-65'})

    def clean_email(self):
        email = self.cleaned_data['email']
        user = None

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            pass

        if user:
            self.add_error('email', 'Аккаунт с таким email уже зарегистрирован.')
            self.fields['email'].widget.attrs['class'] = 'is-invalid'

        return email

    def save(self, commit=True):
        user = User.objects.create_user(self.cleaned_data['email'])
        partner = super().save(commit=False)
        partner.date_registered = timezone.now()
        partner.user = user
        if commit:
            partner.save()
        return partner


class CustomAuthForm(AuthenticationForm):
    username = forms.CharField(widget=TextInput(attrs={'class': 'validate', 'placeholder': 'Email'}))
    password = forms.CharField(widget=PasswordInput(attrs={'placeholder': 'Пароль'}))


class SubscribeForm(forms.Form):
    client_email = forms.EmailField()
    period = forms.IntegerField(widget=forms.Select)
    tariff = forms.ChoiceField(choices=())

    def __init__(self, tariffs, quotas, *args, **kwargs):
        super(SubscribeForm, self).__init__(*args, **kwargs)
        self.fields['tariff'].choices = tariffs

        for quota in quotas:
            code = quota['code']
            self.fields[code] = forms.IntegerField(label=quota['name'], min_value=1)

    def clean(self):
        cleaned_data = super().clean()
        period = cleaned_data['period']
        tariff_code = cleaned_data['tariff']
        tariff_json = api_get('https://adesk.ru/api/tariffs').json()

        tariffs = {}
        for t in tariff_json['tariffs']:
            tariffs[t['code']] = t['pricing']

        if str(period) not in tariffs[tariff_code].keys():
            raise ValidationError('input period value не соответствует тарифу')

        return cleaned_data
