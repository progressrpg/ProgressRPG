from django.db import models
from math import sqrt

##########################################################
##### BASIC POSITION
##########################################################


class Position(models.Model):
    x = models.IntegerField(default=0)
    y = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def calculate_distance(self, other):
        return sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def is_near(self, other, threshold=1.0):
        return self.calculate_distance(other) <= threshold

    def set_coordinates(self, x: int, y: int):
        """Change x and y."""
        self.x = x
        self.y = y
        self.save(update_fields=["x", "y"])

    def set_position(self, position: "Position"):
        self.set_coordinates(x=position.x, y=position.y)

    def move_by(self, dx: int, dy: int):
        self.set_coordinates(self.x + dx, self.y + dy)

    def __str__(self):
        return f"Position: {self.x},{self.y}"


class GameWorldObject(models.Model):
    position = models.OneToOneField(Position, on_delete=models.CASCADE, null=True)

    class Meta:
        abstract = True

    def distance_to(self, other):
        if self.position is None or other.position is None:
            raise ValueError("Both objects must have a Position assigned")
        return self.position.calculate_distance(other.position)

    def get_nearby(self, queryset, radius):
        """
        Returns objects from the given queryset that lie within a radius.
        """
        nearby = []
        for obj in queryset:
            if (
                obj.position
                and self.position.calculate_distance(obj.position) <= radius
            ):
                nearby.append(obj)
        return nearby


class Movable(GameWorldObject):
    movement_speed = models.FloatField(default=1.0)
    is_moving = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def move_to(self, new_position: Position, speed_modifier: float = 1.0) -> float:
        if not self.position:
            raise ValueError(
                "Movable object must have a Position assigned before moving"
            )
        distance = self.position.calculate_distance(new_position)
        travel_time = distance / (self.movement_speed * speed_modifier)
        self.position.set_position(new_position)
        self.is_moving = False
        self.save(update_fields=["is_moving"])
        return travel_time


##########################################################
##### BASIC LOCATION
##########################################################


class Location(GameWorldObject):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Building(GameWorldObject):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default="")
    population_centre = models.ForeignKey(
        "locations.PopulationCentre",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="buildings",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Area(models.Model):
    # from character.models import Character
    name = models.CharField(max_length=100)
    # characters = models.ManyToManyField(Character, blank=True)
    buildings = models.ManyToManyField(Building, blank=True)


class PopulationCentre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    position = models.OneToOneField(
        Position, on_delete=models.CASCADE, null=True, blank=True
    )
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
