from django.db import models
from django.utils.formats import date_format

from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser, PermissionsMixin
)


class MyUserManager(BaseUserManager):
    def create_user(self, email, password=None):
        """
        Creates and saves a User with the given email
        """
        if not email:
            raise ValueError('Users must have an email and password')

        user = self.model(
            email=email,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None):
        """
        Creates and saves a User with the given email
        """
        user = self.create_user(
            email=email,
            password=password
        )
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=False, verbose_name="Активирован")
    is_staff = models.BooleanField(default=False, verbose_name="Полномочия администратора")
    date_activated = models.DateTimeField(verbose_name="Дата активации", null=True)

    objects = MyUserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email

    def generate_and_change_password(self):
        password = User.objects.make_random_password()
        self.set_password(password)
        self.save(update_fields=['password'])
        return password


class Partner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    inn = models.CharField(max_length=32, verbose_name="ИНН")
    phone_number = models.CharField(max_length=32, verbose_name="Номер телефона")
    first_name = models.CharField(max_length=32, verbose_name="Имя")
    last_name = models.CharField(max_length=32, verbose_name="Фамилия")
    company_name = models.CharField(max_length=128, null=True, blank=True, verbose_name="Наименование компании")
    debt = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Задолженность")
    contract_number = models.CharField(max_length=32, null=True, blank=True, verbose_name="Номер договора")
    commission = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, verbose_name="Процент "
                                                                                                         "комиссии")
    date_registered = models.DateTimeField(verbose_name="Дата подачи заявки", null=True)

    def __str__(self):
        name = f"{self.first_name} {self.last_name}"
        if self.company_name is None:
            return name
        return f"{self.company_name}"


class Subscription(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, verbose_name="Партнёр")
    email = models.EmailField()
    cost_value = models.IntegerField(verbose_name="Итоговая стоимость")
    commission = models.DecimalField(max_digits=3, decimal_places=1, verbose_name="Процент комиссии")
    reg_date = models.DateTimeField(verbose_name="Дата оформления")
    period = models.IntegerField(verbose_name="Период (мес.)")
    tariff = models.CharField(max_length=32, verbose_name="Тариф")
    quotas = models.JSONField(null=True, blank=True, verbose_name="Квоты")

    def __str__(self):
        return self.email

    @property
    def revenue(self):
        return self.cost_value * self.commission / 100
