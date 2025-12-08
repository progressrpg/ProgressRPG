from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.db import models
from math import sqrt

##########################################################
##### MIXIN
##########################################################


class Movable(models.Model):
    movement_speed = models.FloatField(default=1.0)
    location = gis_models.PointField(srid=3857, default=Point(0, 0, srid=3857))
    is_moving = models.BooleanField(default=False)
    target_location = gis_models.PointField(srid=3857, blank=True, null=True)

    class Meta:
        abstract = True

    def move_to(self, new_location: Point, speed_modifier: float = 1.0):
        if not self.location:
            raise ValueError(
                "Movable object must have a location assigned before moving"
            )
        distance = self.location.distance(new_location)
        travel_time = distance / (self.movement_speed * speed_modifier)
        self.location = new_location
        self.save(update_fields=["location"])
        return travel_time

    def step_toward(self, time_delta: float = 1.0, speed_modifier: float = 1.0):
        """Move a fraction toward target based on time_delta and movement speed"""
        if not self.target_location:
            self.is_moving = False
            self.save(update_fields=["is_moving"])
            return False

        dx = self.target_location.x - self.location.x
        dy = self.target_location.y - self.location.y
        distance = (dx**2 + dy**2) ** 0.5
        max_distance = self.movement_speed * speed_modifier * time_delta
        distance_travelled = 0

        if distance <= max_distance:
            distance_travelled = distance
            self.location = self.target_location
            self.is_moving = False
        else:
            distance_travelled = max_distance
            factor = max_distance / distance
            new_x = self.location.x + dx * factor
            new_y = self.location.y + dy * factor
            self.location = Point(new_x, new_y, srid=self.location.srid)
            self.is_moving = True

        self.save(update_fields=["location", "is_moving"])
        return self.is_moving, distance_travelled

    def nearby_objects(self, queryset, radius: float):
        """Return objects from queryset within radius of self."""
        return (
            queryset.annotate(dist=Distance("location", self.location))
            .filter(dist__lte=radius)
            .order_by("dist")
        )


##########################################################
##### BASIC LOCATION
##########################################################


class Building(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default="")
    location = gis_models.PointField(
        srid=3857, default=Point(0, 0, srid=3857), help_text="Entrance location"
    )
    footprint = gis_models.PolygonField(null=True, blank=True, srid=3857)

    population_centre = models.ForeignKey(
        "locations.PopulationCentre",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="buildings",
    )

    def __str__(self):
        return self.name


class PopulationCentre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    location = gis_models.PointField(srid=3857, default=Point(0, 0, srid=3857))
    boundary = gis_models.PolygonField(null=True, blank=True, srid=3857)

    def __str__(self):
        return self.name

    @property
    def building_count(self):
        return self.buildings.count()

