from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context as allauth_context
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site

from users.tasks import send_rendered_email_task


class CustomAccountAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix: str, email: str, context: dict) -> None:
        request = allauth_context.request
        ctx = {
            "request": request,
            "email": email,
        }
        if request is not None:
            ctx["current_site"] = get_current_site(request)
        ctx.update(context)

        msg = self.render_mail(template_prefix, email, ctx)

        plain_message = ""
        html_message = ""
        if getattr(msg, "content_subtype", "plain") == "html":
            html_message = msg.body
        else:
            plain_message = msg.body

        for alternative in getattr(msg, "alternatives", []):
            content = getattr(alternative, "content", alternative[0])
            mimetype = getattr(alternative, "mimetype", alternative[1])
            if mimetype == "text/html":
                html_message = content

        send_rendered_email_task.delay(
            recipient_list=msg.to,
            subject=msg.subject,
            plain_message=plain_message,
            html_message=html_message,
            from_email=msg.from_email,
            headers=msg.extra_headers or None,
        )

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
