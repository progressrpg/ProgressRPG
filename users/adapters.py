from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site


class CustomAccountAdapter(DefaultAccountAdapter):
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        activate_url = f"{settings.FRONTEND_URL}/confirm_email/{emailconfirmation.key}"
        ctx = {
            "user": emailconfirmation.email_address.user,
            "current_site": get_current_site(request),
            "key": emailconfirmation.key,
            "activate_url": activate_url,
        }

        if signup:
            email_template = "account/email/email_confirmation_signup"
        else:
            email_template = "account/email/email_confirmation"

        self.send_mail(email_template, emailconfirmation.email_address.email, ctx)

    def get_reset_password_from_key_url(self, key):
        return f"{settings.FRONTEND_URL.rstrip('/')}/reset-password/{key}"
