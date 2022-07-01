from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.views import View

from ..forms import PartnerRegistrationForm, CustomAuthForm


class RegistrationView(View):
    template_name = 'partner/auth/registration.html'

    def get(self, request):
        form = PartnerRegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PartnerRegistrationForm(request.POST)

        if form.is_valid():
            form.save()
            request.session['pp_redarekt'] = True
            return redirect('partner:success_registration')

        return render(request, self.template_name, {'form': form})


def success_registration(request):
    if 'pp_redarekt' in request.session:
        del request.session['pp_redarekt']
        return render(request, template_name='partner/auth/success_registration.html')

    return redirect('partner:registration')


class MyLoginView(LoginView):
    template_name = 'partner/auth/login.html'
    next_page = 'partner:account_profile'
    redirect_authenticated_user = True
    authentication_form = CustomAuthForm
