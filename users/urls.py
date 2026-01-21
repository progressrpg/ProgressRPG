# All non-API Django template view URLs have been removed.
# The frontend now uses REST API endpoints exclusively at /api/v1/
# Password reset URLs are kept as they may still be needed for email-based flows

from django.contrib.auth import views as auth_views
from django.urls import path

urlpatterns = [
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email_plain.txt",
            html_email_template_name="registration/password_reset_email_html.html",
            subject_template_name="registration/password_reset_email_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "password_reset/done",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
