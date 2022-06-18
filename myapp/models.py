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
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_activated = models.DateTimeField('date activated', null=True)

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
    INN = models.CharField(max_length=32)
    phone_number = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)
    last_name = models.CharField(max_length=32)
    company_name = models.CharField(max_length=64, null=True, blank=True)
    debt = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    contract_number = models.CharField(max_length=32, null=True, blank=True)
    commission = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    date_registered = models.DateTimeField('date registered')

    def __str__(self):
        name = f"{self.first_name} {self.last_name}"
        if self.company_name is None:
            return name
        return f"{self.company_name}"


class Subscription(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE)
    email = models.EmailField()
    cost_value = models.IntegerField()
    commission = models.DecimalField(max_digits=3, decimal_places=1)
    reg_date = models.DateTimeField()
    period = models.IntegerField()
    tariff = models.CharField(max_length=32)
    quotas = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.email

    @property
    def revenue(self):
        return self.cost_value * self.commission / 100
