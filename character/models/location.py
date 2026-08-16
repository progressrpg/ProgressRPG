from django.db import models
from django.db.models import Q


class CharacterLocation(models.Model):
    """
    Where a character's home or work is - the source of truth for commute
    scheduling (see locations/services/schedule.py).
    """

    class Role(models.TextChoices):
        HOME = "home", "Home"
        WORK = "work", "Work"

    character = models.ForeignKey(
        "character.Character",
        on_delete=models.CASCADE,
        related_name="locations",
    )
    location = models.ForeignKey(
        "locations.Building",
        on_delete=models.CASCADE,
        related_name="character_locations",
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    is_primary = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["character", "role"],
                condition=Q(is_primary=True),
                name="one_primary_location_per_character_role",
            ),
        ]

    def __str__(self):
        return f"{self.character} - {self.role} @ {self.location}"
