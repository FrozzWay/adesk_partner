from django import forms
from django.contrib import admin, messages
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.template import Engine, Context
from django.utils import timezone
from django.core.mail import EmailMessage
from django_object_actions import DjangoObjectActions

from .models import User, Partner, Subscription


class UserCreationForm(forms.ModelForm):
    password_field = forms.CharField(required=False, label='Пароль', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = "__all__"
        help_texts = {"is_active": "Пользователь не сможет авторизоваться и подписывать клиентов, если неактивен.",
                      "is_staff": "Не устанавливать для партнёров!"}

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data["password_field"]
        is_active = self.cleaned_data['is_active']
        if is_active:
            user.date_activated = timezone.now()
        user.set_password(password if password else None)
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password_field = forms.CharField(required=False, label='Новый пароль', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('email', 'is_active',)
        help_texts = {"is_active": "Пользователь не сможет авторизоваться и подписывать клиентов, если неактивен."}

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data['password_field']
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class PartnerInline(admin.StackedInline):
    model = Partner
    can_delete = False
    readonly_fields = ('date_registered',)


class UserAdmin(DjangoObjectActions, BaseUserAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    inlines = [PartnerInline]

    change_actions = ('deactivate', 'make_active', 'send_credentials_via_email')

    @admin.display(description="Партнёр")
    def partner_d(self, obj):
        return obj.partner.__str__()

    @admin.display(description="Дата подачи заявки")
    def date_registered(self, obj):
        return obj.partner.date_registered

    # The fields to be used in displaying the User model.
    list_display = ('__str__', 'partner_d', 'date_registered', 'is_active', 'date_activated')
    list_filter = ('is_staff',)
    readonly_fields = ('password', 'email')
    fieldsets = (
        (None, {'fields': ('email', 'password_field')}),
        ('Права', {'fields': ('is_active',)}),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.

    add_fieldsets = (
        (None, {'fields': ('email', 'password_field')}),
        ('Права', {'fields': ('is_active', 'is_staff')}),
    )

    search_fields = ['email', 'partner__first_name', 'partner__last_name', 'partner__company_name']

    ordering = ('is_active',)
    filter_horizontal = ()

    # Generate new password and send credentials to partner's email
    def send_credentials_via_email(self, request, obj):
        password = obj.generate_and_change_password()
        # ... send credentials via email ...
        template = (Engine.get_default()).get_template('partner/email.html')
        context = Context({
            "title": "Завершение регистрации Adesk Partner",
            "text": f"Теперь вы можете войти в личный кабинет партнёра."
                    f"<br><br>Логин: {obj.email}"
                    f"<br>Пароль: {password}",
            "link_text": "Войти",
            "link_url": ""
        })
        email = EmailMessage(
            subject="Данные для входа в личный кабинет Adesk Partner",
            body=template.render(context),
            to=[obj.email],
        )
        email.content_subtype = "html"
        if email.send(fail_silently=True):
            self.message_user(request, "Данные для входа отправлены.",
                              level=messages.SUCCESS)
        else:
            self.message_user(request, "Отправить данные для входа не удалось.",
                              level=messages.ERROR)

    def make_active(self, request, obj):
        obj.is_active = True
        obj.date_activated = timezone.now()
        obj.save(update_fields=['is_active', 'date_activated'])
        self.message_user(request, "Аккаунт активирован", level=messages.SUCCESS)

    make_active.label = "Активировать"

    def deactivate(self, request, obj):
        obj.is_active = False
        obj.date_activated = None
        obj.save(update_fields=['is_active', 'date_activated'])
        self.message_user(request, "Аккаунт деактивирован", level=messages.WARNING)

    deactivate.label = "Деактивировать"


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'partner', 'cost_value', 'commission', 'reg_date', 'period', 'tariff')
    search_fields = ['partner__first_name', 'partner__last_name', 'partner__company_name', 'email', 'tariff']

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(User, UserAdmin)
admin.site.register(Subscription, SubscriptionAdmin)

admin.site.unregister(Group)
