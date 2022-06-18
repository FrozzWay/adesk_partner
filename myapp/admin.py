from django import forms
from django.contrib import admin, messages
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils import timezone
from django_object_actions import DjangoObjectActions

from .models import User, Partner, Subscription


class UserCreationForm(forms.ModelForm):
    """A form for creating new users through admin."""

    password_field = forms.CharField(required=False, label='Password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = "__all__"

    def save(self, commit=True):
        user = super().save(commit=False)
        emptyStr_to_None = lambda i: i or None
        password = emptyStr_to_None(self.cleaned_data["password_field"])
        user.set_password(password)
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Replaces the password field with admin's
    disabled password hash display field.
    """

    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ('email', 'is_active')
        help_texts = {"is_active": "While active partner will be allowed to checkout clients"}


class PartnerInline(admin.StackedInline):
    model = Partner
    can_delete = False


class UserAdmin(DjangoObjectActions, BaseUserAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    inlines = [PartnerInline]

    change_actions = ('deactivate', 'make_active', 'send_credentials_via_email')

    @admin.display()
    def partner(self, obj):
        return obj.partner.__str__()

    @admin.display()
    def date_registered(self, obj):
        return obj.partner.date_registered

    # The fields to be used in displaying the User model.
    list_display = ('__str__', 'partner', 'date_registered', 'is_active', 'date_activated')
    list_filter = ('is_staff',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_active',)}),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password_field', 'is_active'),
        }),
    )

    search_fields = ['email', 'partner__first_name', 'partner__last_name', 'partner__company_name']

    ordering = ('is_active',)
    filter_horizontal = ()

    # Generate new password and send credentials to partner's email
    def send_credentials_via_email(self, request, obj):
        password = obj.generate_and_change_password()
        print(password)
        # ... send credentials via email ...
        self.message_user(request, "Credentials were successfully sent to partner's email",
                          level=messages.SUCCESS)

    def make_active(self, request, obj):
        obj.is_active = True
        obj.date_activated = timezone.now()
        obj.save(update_fields=['is_active', 'date_activated'])
        self.message_user(request, "Account set to active", level=messages.SUCCESS)
    make_active.label = "Activate"

    def deactivate(self, request, obj):
        obj.is_active = False
        obj.date_activated = None
        obj.save(update_fields=['is_active', 'date_activated'])
        self.message_user(request, "Account deactivated", level=messages.SUCCESS)


class PartnerAdmin(admin.ModelAdmin):
    # Hide model from admin page
    get_model_perms = lambda self, req: {}


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'partner', 'cost_value', 'commission', 'reg_date', 'period', 'tariff')
    search_fields = ['partner__first_name', 'partner__last_name', 'partner__company_name', 'email', 'tariff']


admin.site.register(User, UserAdmin)
admin.site.register(Partner, PartnerAdmin)
admin.site.register(Subscription, SubscriptionAdmin)

admin.site.unregister(Group)
