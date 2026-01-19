from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
import logging

from .models import CustomUser, Profile, InviteCode

logger = logging.getLogger("general")


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    invite_code = forms.CharField(required=True)
    agree_to_terms = forms.BooleanField(
        required=True,
        label="I agree to the terms and conditions.",  # Template doesn't use this label
        error_messages={
            "required": "You must agree to the terms and conditions to register."
        },
    )

    class Meta:
        model = CustomUser
        fields = ["email", "password1", "password2"]

    def clean_invite_code(self):
        code = self.cleaned_data["invite_code"].strip()
        try:
            invite = InviteCode.objects.get(code=code)
        except InviteCode.DoesNotExist:
            raise ValidationError("Invalid or inactive invite code.")

        if not invite.is_valid():
            raise ValidationError(
                "This invite code has already been used or is invalid."
            )

        self.cleaned_data["_invite"] = invite
        return code

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            invite = self.cleaned_data.get("_invite")
            if invite:
                invite.use()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email address", max_length=254)

    def clean(self):
        try:
            email = self.cleaned_data.get("username")
            password = self.cleaned_data.get("password")
            logger.info(
                f"[EMAIL AUTHENTICATION FORM] Attempting authentication for email {email}."
            )

            if email and password:
                self.user_cache = authenticate(username=email, password=password)
                if self.user_cache is None:
                    logger.warning(
                        f"[EMAIL AUTHENTICATION FORM] Authentication failed for email {email}."
                    )
                    raise forms.ValidationError(
                        self.error_messages["invalid_login"],
                        code="invalid_login",
                        params={"username": self.username_field.verbose_name},
                    )
                else:
                    logger.debug(
                        f"[EMAIL AUTHENTICATION FORM] Authentication successful for email {email}."
                    )
                    self.confirm_login_allowed(self.user_cache)
            return self.cleaned_data
        except forms.ValidationError as e:
            logger.warning(f"[EMAIL AUTHENTICATION FORM] Validation error: {e}")
            raise
        except Exception as e:
            logger_errors = logging.getLogger("errors")
            logger_errors.exception(f"[EMAIL AUTHENTICATION FORM] Unexpected error: {e}")
            raise forms.ValidationError(
                "An unexpected error occurred during authentication."
            )


class ProfileForm(forms.ModelForm):
    name = forms.CharField(required=True, label="Required. Enter a username.")

    class Meta:
        model = Profile
        fields = ["name", "bio"]
