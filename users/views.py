from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required

# from django.contrib.sessions.models import Session
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponse, JsonResponse  # , HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.timezone import now, timedelta
from django.views.decorators.cache import cache_page
from django.views.generic.edit import CreateView, FormView
from django_filters.rest_framework import DjangoFilterBackend
from django_ratelimit.decorators import ratelimit
import json, logging
from rest_framework import viewsets, mixins, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import ProfileFilter
from .forms import UserRegisterForm, ProfileForm, EmailAuthenticationForm
from .models import Profile
from .serializers import ProfileSerializer
from .utils import kick_old_sessions, send_signup_email

from api.views import IsOwnerProfile
from character.models import PlayerCharacterLink
from gameplay.serializers import ActivitySerializer

logger = logging.getLogger("django")


# Index view
@cache_page(60 * 15)
def index_view(request):
    """
    Render the homepage (index) view.

    :param request: The HTTP request object.
    :type request: django.http.HttpRequest
    :return: An HTTP response rendering the index template.
    :rtype: django.http.HttpResponse
    """
    return render(request, "users/index.html")


def get_client_ip(request):
    """
    Retrieve the IP address of the client making the request.

    :param request: The HTTP request object.
    :type request: django.http.HttpRequest
    :return: The IP address of the client.
    :rtype: str
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


# Login view
@method_decorator(
    ratelimit(key="ip", rate="10/m", method="POST", block=True), name="dispatch"
)
class LoginView(FormView):
    """
    Handle user login using an email-based authentication form.

    Attributes:
        template_name (str): The path to the login template.
        form_class (Form): The form class used for email authentication.
        success_url (str): The URL to redirect to upon successful login.
    """

    template_name = "users/login.html"
    form_class = EmailAuthenticationForm
    success_url = reverse_lazy("game")

    def form_valid(self, form):
        """
        Process a valid login form, logging in the user and redirecting based on onboarding progress.

        :param form: The valid login form instance.
        :type form: EmailAuthenticationForm
        :return: An HTTP response redirecting to the appropriate onboarding step or game.
        :rtype: django.http.HttpResponseRedirect
        :raises ValueError: If the user's onboarding step is invalid.
        """
        user = form.get_user()
        logger.info(
            f"[LOGIN VIEW] Successful login for user: {user.email} (ID: {user.id})"
        )
        login(self.request, user)
        self.request.session.save()

        kick_old_sessions(user, self.request.session.session_key)

        # If the user has initiated account deletion, cancel it
        if user.pending_delete and user.delete_at > now():
            user.pending_delete = False
            user.delete_at = None  # Clear the scheduled deletion timestamp
            user.save()

        if user.profile.onboarding_step != 5:
            logger.debug(
                f"User {user.email} onboarding step: {user.profile.onboarding_step}"
            )
            match user.profile.onboarding_step:
                case 0 | 1:
                    return redirect("create_profile")
                case 2:
                    return redirect("link_character")
                case 3:
                    return redirect("subscribe")
                case 4:
                    return redirect("game")
                case _:
                    logger.error(
                        f"Invalid onboarding step for user {user.id}: {user.profile.onboarding_step}"
                    )
                    raise ValueError("Onboarding step number incorrect")
                    return redirect("index")
        else:
            return redirect("game")

    def form_invalid(self, form):
        """
        Handle an invalid login form submission.

        :param form: The invalid login form instance.
        :type form: EmailAuthenticationForm
        :return: An HTTP response rendering the login form with error messages.
        :rtype: django.http.HttpResponse
        """
        logger.warning(
            f"Failed login attempt for email: {self.request.POST.get('email', 'UNKNOWN')}"
        )
        messages.error(self.request, "Invalid credentials")
        return self.render_to_response(self.get_context_data(form=form))

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests to display the login form or redirect authenticated users.

        :param request: The HTTP request object.
        :type request: django.http.HttpRequest
        :return: An HTTP response rendering the login form or redirecting authenticated users.
        :rtype: django.http.HttpResponse or django.http.HttpResponseRedirect
        """
        if request.user.is_authenticated:
            logger.info(
                f"User {request.user.email} already logged in, redirecting to game"
            )
            return redirect("game")
        return super().get(request, *args, **kwargs)


# Logout view
def logout_view(request):
    """
    Log out the current user and redirect to the homepage (index view).

    :param request: The HTTP request object.
    :type request: django.http.HttpRequest
    :return: An HTTP response redirecting to the homepage.
    :rtype: django.http.HttpResponseRedirect
    """
    logger.info(f"[LOGOUT VIEW] User {request.user.id} logged out.")
    logout(request)
    return redirect("index")


# Register view
@method_decorator(
    ratelimit(key="ip", rate="10/m", method="POST", block=True), name="dispatch"
)
class RegisterView(CreateView):
    """
    Handle user registration by creating a new `CustomUser` instance
    and redirecting to the profile creation page.

    Attributes:
        model (Model): The user model to create an instance of.
        form_class (Form): The form class used to handle user registration.
        template_name (str): The path to the registration template.
        success_url (str): The URL to redirect to upon successful registration.
    """

    model = get_user_model()
    form_class = UserRegisterForm
    template_name = "users/register.html"
    success_url = reverse_lazy("create_profile")

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests to display the registration form or redirect authenticated users.

        :param request: The HTTP request object.
        :type request: django.http.HttpRequest
        :return: An HTTP response rendering the registration form or redirecting authenticated users.
        :rtype: django.http.HttpResponse or django.http.HttpResponseRedirect
        """
        if not self.is_registration_enabled():
            return redirect("registration_disabled")
        return super().get(request, *args, **kwargs)

    def is_registration_enabled(self) -> bool:
        """
        Check if user registration is enabled.

        :return: True if registration is enabled, False otherwise.
        :rtype: bool
        """
        return getattr(settings, "REGISTRATION_ENABLED", True)

    def form_valid(self, form) -> HttpResponse:
        """
        Process a valid registration form, create the user, log them in, and send a welcome email.

        :param form: The valid registration form instance.
        :type form: UserRegisterForm
        :return: A redirect to the profile creation page.
        :rtype: django.http.HttpResponseRedirect
        """

        user = form.save()
        logger.info(f"User registered successfully: {user.email} (ID: {user.id})")

        user = authenticate(
            username=user.email, password=form.cleaned_data["password1"]
        )
        if user is not None:
            login(self.request, user)
            logger.info(f"User {user.email} authenticated and logged in successfully.")
            send_signup_email(user)
        else:
            logger.warning(f"Authentication failed for user {user}.")

        return redirect(self.success_url)

    def form_invalid(self, form) -> HttpResponse:
        """
        Handle the case when the registration form is invalid, logging the error and re-rendering the form.
        """
        logger.error(f"Invalid registration form submitted: {form.errors}")
        return self.render_to_response(self.get_context_data(form=form))


def registration_disabled_view(request):
    """
    Render a page indicating that registration is disabled.

    :param request: The HTTP request object.
    :type request: django.http.HttpRequest
    :return: An HTTP response rendering the registration disabled template.
    :rtype: django.http.HttpResponse
    """
    return render(request, "users/registration_disabled.html")


# Create profile view
@transaction.atomic
@login_required
def create_profile_view(request):
    """
    Handle the creation and setup of the user's profile, including setting a name
    and saving the first onboarding step.

    :param request: The HTTP request object.
    :type request: django.http.HttpRequest
    :return: An HTTP response rendering the profile creation form or redirecting to link_character.
    :rtype: django.http.HttpResponse or django.http.HttpResponseRedirect
    """
    profile = Profile.objects.get(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()

            logger.info(
                f"Profile updated for user {request.user.username} (ID: {request.user.id})"
            )

            profile.name = form.cleaned_data["name"]
            profile.onboarding_step = 2
            profile.save()

            logger.debug(
                f"Name set to '{profile.name}' and onboarding step set to 2 for user {request.user.username}."
            )

            return redirect("link_character")
        else:
            logger.warning(
                f"Profile form validation failed for user {request.user.username}."
            )

    else:
        form = ProfileForm(instance=profile)
    return render(request, "users/create_profile.html", {"form": form})


@transaction.atomic
@login_required
def link_character_view(request):
    """
    Handle the linking of an active character to the user's profile and updating the onboarding step.

    :param request: The HTTP request object.
    :type request: django.http.HttpRequest
    :return: An HTTP response rendering the link character page or redirecting to the profile creation page.
    :rtype: django.http.HttpResponse or django.http.HttpResponseRedirect
    """
    profile = request.user.profile
    if request.method == "POST":
        profile.onboarding_step = 3
        profile.save()

        logger.info(
            f"User {request.user.username} (ID: {request.user.id}) updated onboarding_step to 3."
        )

        return redirect("tutorial")
    else:
        link = PlayerCharacterLink.objects.filter(
            profile=profile, is_active=True
        ).first()

        if link is None:
            logger.warning(
                f"User {request.user.username} (ID: {request.user.id}) has no active character link."
            )
            return redirect("create_profile")  # or any other appropriate redirect

        character = link.character

        logger.debug(
            f"User {request.user.username} (ID: {request.user.id}) linked character '{character.name}' (ID: {character.id})."
        )

    return render(request, "users/link_character.html", {"char_name": character.name})


@login_required
def tutorial_view(request):
    user = request.user
    if request.method == "POST":
        user.profile.onboarding_step = 4
        user.profile.save()
        return redirect("game")
    return render(request, "users/tutorial.html")


# Profile view
@login_required
def profile_view(request):
    """
    Display the user's profile page with details such as total time spent on activities.

    :param request: The HTTP request object.
    :type request: django.http.HttpRequest
    :return: An HTTP response rendering the profile page.
    :rtype: django.http.HttpResponse
    """
    profile = request.user.profile
    total_minutes = round(profile.total_time / 60)

    character = PlayerCharacterLink().get_character(profile)

    logger.info(
        f"User {request.user.username} (ID: {request.user.id}) viewed their profile. Total time spent: {total_minutes} minutes."
    )

    return render(
        request,
        "users/profile.html",
        {"profile": profile, "character": character, "total_minutes": total_minutes},
    )


# Edit profile view
@transaction.atomic
@login_required
def edit_profile_view(request):
    """
    Allow the user to edit and update their profile information.

    :param request: The HTTP request object.
    :type request: django.http.HttpRequest
    :return: An HTTP response rendering the edit profile form or redirecting to the profile page.
    :rtype: django.http.HttpResponse or django.http.HttpResponseRedirect
    """
    profile = Profile.objects.get(user=request.user)

    logger.info(
        f"User {request.user.username} (ID: {request.user.id}) is editing their profile."
    )

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            logger.info(
                f"User {request.user.username} (ID: {request.user.id}) successfully updated their profile."
            )
            return redirect("profile")
        else:
            logger.warning(
                f"User {request.user.username} (ID: {request.user.id}) failed to update their profile. Form is invalid."
            )
    else:
        form = ProfileForm(instance=profile)
    return render(request, "users/edit_profile.html", {"form": form})


# Download user data
@ratelimit(key="ip", rate="10/h", method="POST", block=True)
@login_required
@transaction.atomic
def download_user_data(request):
    """
    Generate and provide a downloadable JSON file containing the user's data,
    including profile, character, and activity details.

    :param request: The HTTP request object.
    :type request: django.http.HttpRequest
    :return: A JSON file response containing the user's data or an error response if character data is missing.
    :rtype: django.http.HttpResponse or django.http.JsonResponse
    :raises character.DoesNotExist: If no character is found for the user.
    """
    user = request.user
    profile = user.profile
    try:
        character = PlayerCharacterLink().get_character(profile)
    except character.DoesNotExist:
        logger.error(f"Character not found for user {user.username} (ID: {user.id}).")
        return JsonResponse({"error": "Character data not found."}, status=404)

    activities_json = ActivitySerializer(profile.activities.all(), many=True).data
    user_data = {
        "username": user.username,
        "email": user.email,
        "profile": {
            "id": profile.id,
            "profile_name": profile.name,
            "level": profile.level,
            "xp": profile.xp,
            "bio": profile.bio,
            "total_time": profile.total_time,
            "total_activities": profile.total_activities,
            "is_premium": profile.is_premium,
        },
        "activities": activities_json,
        "character": {
            "id": character.id,
            "character_name": character.name,
            "level": character.level,
            "total_quests": character.total_quests,
        },
    }

    logger.info(
        f"User {user.username} (ID: {user.id}) initiated download of their data."
    )

    # Convert to JSON and create a downloadable response
    response = HttpResponse(
        json.dumps(user_data, indent=4),  # Pretty-printed JSON
        content_type="application/json",
    )
    response["Content-Disposition"] = 'attachment; filename="user_data.json"'

    logger.info(
        f"User {user.username} (ID: {user.id}) successfully downloaded their data."
    )

    return response


@login_required
@transaction.atomic
def delete_account(request):
    """
    Initiates the account deletion process by marking the user for deletion in 14 days,
    sending a notification email, and logging the user out.

    :param request: The HTTP request object.
    :type request: django.http.HttpRequest
    :return: An HTTP response redirecting to the index page or rendering the delete account confirmation page.
    :rtype: django.http.HttpResponseRedirect or django.http.HttpResponse
    """
    if request.method == "POST":
        user = request.user

        logger.info(f"User {user.username} (ID: {user.id}) initiated account deletion.")

        user.pending_deletion = True
        user.delete_at = now() + timedelta(days=14)
        user.save()

        send_mail(
            "Account Deletion Scheduled",
            "Hello,\nYour account will be deleted in 14 days. If you wish to cancel the deletion, please log in again.\nThank you for using Progress, and we're sorry to see you go!",
            "admin@progressrpg.com",  # Use your actual email address
            [user.email],
            fail_silently=False,
        )

        request.user.auth_token.delete()
        request.session.flush()
        logout(request)

        logger.info(
            f"[DELETE ACCOUNT] User {user.id} logged out and scheduled for soft delete."
        )

        return redirect("index")
    else:
        return render(request, "users/delete_account.html")


class ProfileViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def me(self, request):
        profile = self.get_queryset().first()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
