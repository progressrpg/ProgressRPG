# progression/mixins.py
from django.utils import timezone


class PlayerOwnedMixin:
    """
    Provides common helper methods for models where players
    can perform CRUD operations.
    """

    def rename(self, new_name: str):
        """Update the instance's name field."""
        if hasattr(self, "name"):
            self.name = new_name
            self.save(update_fields=["name"])
        return self

    def to_dict(self, fields=None):
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
    def list_fields(cls):
        """Return all field names for easier introspection."""
        return [f.name for f in cls._meta.fields]

    @classmethod
    def for_player(cls, player):
        return cls.objects.filter(player=player)

    @classmethod
    def for_player_ids(cls, player):
        return list(cls.objects.filter(player=player).values_list("id", flat=True))

    def touch(self):
        """Update the last_updated timestamp if present."""
        if hasattr(self, "last_updated"):
            self.last_updated = timezone.now()
            self.save(update_fields=["last_updated"])
        return self
