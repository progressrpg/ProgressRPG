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

    class Meta:
        abstract = True

    def move_to(self, new_location: Point, speed_modifier: float = 1.0):
        if not self.location:
            raise ValueError(
                "Movable object must have a Position assigned before moving"
            )
        distance = self.location.distance(new_location)
        travel_time = distance / (self.movement_speed * speed_modifier)
        self.location = new_location
        self.is_moving = False
        self.save(update_fields=["location", "is_moving"])
        return travel_time

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
