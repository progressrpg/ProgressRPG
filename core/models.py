import io
import uuid

from django.core.exceptions import ValidationError
from django.core.files.storage import Storage
from django.db import models
from django.urls import reverse
from django.utils.deconstruct import deconstructible


class StoredFile(models.Model):
    """Raw file data stored in the database. Served via core:stored-file."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data = models.BinaryField()
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, default="application/octet-stream")

    def __str__(self):
        return self.filename


@deconstructible
class DatabaseFileStorage(Storage):
    def _save(self, name, content):
        import mimetypes

        content_type, _ = mimetypes.guess_type(name)
        stored = StoredFile.objects.create(
            data=content.read(),
            filename=name.rsplit("/", 1)[-1],
            content_type=content_type or "application/octet-stream",
        )
        return str(stored.pk)

    def _open(self, name, mode="rb"):
        try:
            stored = StoredFile.objects.get(pk=name)
        except (StoredFile.DoesNotExist, ValueError):
            return io.BytesIO(b"")
        return io.BytesIO(bytes(stored.data))

    def exists(self, name):
        try:
            uuid.UUID(name)
        except (ValueError, AttributeError):
            return False
        return StoredFile.objects.filter(pk=name).exists()

    def url(self, name):
        try:
            uuid.UUID(name)
        except (ValueError, AttributeError):
            return ""
        return reverse("core:stored-file", args=[name])

    def delete(self, name):
        StoredFile.objects.filter(pk=name).delete()

    def size(self, name):
        try:
            stored = StoredFile.objects.get(pk=name)
        except (StoredFile.DoesNotExist, ValueError):
            return 0
        return len(stored.data)


class Image(models.Model):
    image = models.ImageField(storage=DatabaseFileStorage(), upload_to="")
    alt_text = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.alt_text or str(self.image)


class GameSettings(models.Model):
    free_timer_limit_seconds = models.IntegerField(default=1800)
    daily_login_base_xp = models.IntegerField(default=10)
    daily_login_streak_step_xp = models.IntegerField(default=2)
    daily_login_max_xp = models.IntegerField(default=20)
    premium_activity_xp_multiplier = models.DecimalField(
        max_digits=5, decimal_places=2, default="2.00"
    )
    default_activity_xp_per_second = models.DecimalField(
        max_digits=5, decimal_places=4, default="1.0000"
    )
    task_activity_xp_multiplier = models.DecimalField(
        max_digits=5, decimal_places=2, default="1.25"
    )
    task_completion_xp = models.IntegerField(default=100)
    xp_mastery_scale = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default="1000.00",
        help_text=(
            "Skill XP needed for the Activity Points mastery multiplier to "
            "grow by +1.0x (see progression.points.xp_mastery_multiplier)."
        ),
    )
    xp_mastery_multiplier_cap = models.DecimalField(
        max_digits=5, decimal_places=2, default="3.00"
    )
    activity_compaction_cutoff_days = models.IntegerField(
        default=90,
        help_text=(
            "Completed CharacterActivity rows older than this are rolled "
            "into CharacterActivityArchive monthly summaries and deleted "
            "(see progression.tasks.compact_character_activities)."
        ),
    )
    activity_search_includes_tasks = models.BooleanField(default=False)
    trial_period_days = models.IntegerField(default=14)
    registration_cap = models.IntegerField(default=1_000_000_000)
    registration_enabled = models.BooleanField(default=True)
    self_serve_registration = models.BooleanField(default=False)
    waitlist_nudges_enabled_from = models.DateTimeField(null=True, blank=True)

    class WaitlistSignupProvider(models.TextChoices):
        MAILCHIMP = "mailchimp", "Mailchimp"
        INTERNAL = "internal", "Internal"

    waitlist_signup_provider = models.CharField(
        max_length=20,
        choices=WaitlistSignupProvider.choices,
        default=WaitlistSignupProvider.MAILCHIMP,
    )

    class Meta:
        verbose_name = "Game settings"
        verbose_name_plural = "Game settings"

    def __str__(self):
        return "Game settings"

    @classmethod
    def current(cls):
        settings, _created = cls.objects.get_or_create(pk=1)
        return settings

    def clean(self):
        if GameSettings.objects.exclude(pk=self.pk).exists():
            raise ValidationError("Only one GameSettings instance allowed")

        errors = {}
        if self.free_timer_limit_seconds < 0:
            errors["free_timer_limit_seconds"] = "Must be non-negative."
        if self.daily_login_base_xp < 0:
            errors["daily_login_base_xp"] = "Must be non-negative."
        if self.daily_login_streak_step_xp < 0:
            errors["daily_login_streak_step_xp"] = "Must be non-negative."
        if self.daily_login_max_xp < 0:
            errors["daily_login_max_xp"] = "Must be non-negative."
        if self.daily_login_max_xp < self.daily_login_base_xp:
            errors["daily_login_max_xp"] = "Must be >= daily_login_base_xp."
        if self.premium_activity_xp_multiplier <= 0:
            errors["premium_activity_xp_multiplier"] = "Must be > 0."
        if self.default_activity_xp_per_second <= 0:
            errors["default_activity_xp_per_second"] = "Must be > 0."
        if self.task_activity_xp_multiplier <= 0:
            errors["task_activity_xp_multiplier"] = "Must be > 0."
        if self.task_completion_xp < 0:
            errors["task_completion_xp"] = "Must be non-negative."
        if self.xp_mastery_scale <= 0:
            errors["xp_mastery_scale"] = "Must be > 0."
        if self.xp_mastery_multiplier_cap < 1:
            errors["xp_mastery_multiplier_cap"] = "Must be >= 1."
        if self.activity_compaction_cutoff_days <= 0:
            errors["activity_compaction_cutoff_days"] = "Must be > 0."
        if self.trial_period_days < 0:
            errors["trial_period_days"] = "Must be non-negative."
        if self.registration_cap < 0:
            errors["registration_cap"] = "Must be non-negative."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        previous_cap = None
        if self.pk:
            previous_cap = (
                GameSettings.objects.filter(pk=self.pk)
                .values_list("registration_cap", flat=True)
                .first()
            )
        super().save(*args, **kwargs)
        if previous_cap is not None and self.registration_cap > previous_cap:
            from django.db import transaction
            from users.tasks import invite_waitlist_entries

            transaction.on_commit(lambda: invite_waitlist_entries.delay())


class AnnouncementQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    summary = models.CharField(max_length=300, blank=True)
    body = models.TextField()
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AnnouncementQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title


class PlayerAnnouncementState(models.Model):
    player = models.ForeignKey(
        "users.Player",
        on_delete=models.CASCADE,
        related_name="announcement_states",
    )
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name="player_states",
    )
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("player", "announcement")

    def __str__(self):
        return f"{self.player_id}:{self.announcement_id}"

    @classmethod
    def unread_count_for_player(cls, player):
        read_ids = cls.objects.filter(
            player=player,
            read_at__isnull=False,
        ).values_list("announcement_id", flat=True)
        return Announcement.objects.published().exclude(id__in=read_ids).count()
