# progression/mixins.py
from typing import Any, TypeVar
from collections.abc import Iterable

from django.db import models
from django.db.models import QuerySet
from django.utils import timezone

T = TypeVar("T", bound="PlayerOwnedMixin")


class PlayerOwnedMixin(models.Model):
    """
    Provides common helper methods for models where players
    can perform CRUD operations.
    """

    class Meta:
        abstract = True

    def rename(self, new_name: str):
        """Update the instance's name field."""
        if hasattr(self, "name"):
            self.name = new_name
            self.save(update_fields=["name"])
        return self

    def to_dict(self, fields: Iterable[str] | None = None) -> dict[str, Any]:
        """
        Return a dictionary representation of the instance.
        If `fields` is provided, only include those fields.
        """
        data = {}
        for field in self._meta.fields:
            fname = field.name
            if fields and fname not in fields:
                continue
            data[fname] = getattr(self, fname)
        return data

    @classmethod
    def list_fields(cls: type[T]) -> list[str]:
        """Return all field names for easier introspection."""
        return [f.name for f in cls._meta.fields]

    @classmethod
    def for_player(cls: type[T], player) -> "QuerySet[T]":
        return cls._default_manager.filter(player=player)

    @classmethod
    def for_player_ids(cls: type[T], player) -> list[int]:
        return list(
            cls._default_manager.filter(player=player).values_list("id", flat=True)
        )

    def touch(self):
        """Update the last_updated timestamp if present."""
        if hasattr(self, "last_updated"):
            self.last_updated = timezone.now()
            self.save(update_fields=["last_updated"])
        return self


class LevelProgressionMixin(models.Model):
    """
    Shared AP/XP behaviour for models with `xp`/`level`/`xp_next_level`/
    `name` fields and an `xp_mods` reverse manager (Player, Character) - the
    curve math and multiplier query live in progression.ap; this just wires
    that up to the instance's own state and persistence.
    """

    # Declared here (not as model fields) so mypy knows the types provided
    # by concrete subclasses (Player, Character) - this mixin is abstract
    # and never instantiated directly.
    level: int
    xp: int
    xp_next_level: int

    class Meta:
        abstract = True

    @property
    def name(self) -> str | None:
        raise NotImplementedError

    def add_xp(self, amount: int):
        """
        Add experience points (XP) to the instance and handle level-up logic.
        """
        from django.db import transaction

        from progression import ap

        with transaction.atomic():
            self.level, self.xp, levelups = ap.apply_xp(self.level, self.xp, amount)
            self.xp_next_level = self.get_xp_for_next_level()
            self.save(update_fields=["xp", "level", "xp_next_level"])
        return [{**event, "person": self, "name": self.name} for event in levelups]

    def get_xp_for_next_level(self):
        """
        Calculate the XP required to reach the next level.
        """
        from progression import ap

        return ap.threshold_for_level(self.level)

    @property
    def total_ap_earned(self):
        """
        Total Activity Points ever earned, reconstructed from level plus the
        current xp-toward-next-level remainder. Level-up thresholds are
        cumulative, so unlike `xp` (which resets on every level-up) this
        stays monotonic - used wherever a long-term progress/prestige figure
        is needed, e.g. village points.
        """
        from progression import ap

        return ap.total_ap_earned(self.level, self.xp)

    def get_xp_multiplier(self, now=None):
        from progression import ap

        return ap.get_multiplier(self, now=now)
