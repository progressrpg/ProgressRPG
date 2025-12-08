from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.db import models
from math import sqrt

##########################################################
##### MOVABLE OBJECTS/BEINGS
##########################################################


class Movable(models.Model):
    movement_speed = models.FloatField(default=1.0)
    location = gis_models.PointField(srid=3857, default=Point(0, 0, srid=3857))
    is_moving = models.BooleanField(default=False)
    target_location = gis_models.PointField(srid=3857, blank=True, null=True)

    # Generic FK for destination object
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="target_movables",
    )
    target_object_id = models.PositiveIntegerField(null=True, blank=True)
    target_object = GenericForeignKey("target_content_type", "target_object_id")

    class Meta:
        abstract = True

    def set_destination(self, obj, use_obj_location=True):
        """
        Assign a target location to this movable object.
        """
        self.target_content_type = ContentType.objects.get_for_model(obj)
        self.target_object_id = obj.pk

        if use_obj_location:
            location_obj = obj
            while True:
                if hasattr(location_obj, "location") and location_obj.location:
                    self.target_location = location_obj.location
                    break

                parent_attr = getattr(location_obj, "parent_for_navigation", None)
                if not parent_attr:
                    self.target_location = None
                    break

                location_obj = getattr(location_obj, parent_attr, None)
                if not location_obj:
                    self.target_location = None
                    break

        self.is_moving = True
        self.save(
            update_fields=[
                "target_content_type",
                "target_object_id",
                "target_location",
                "is_moving",
            ]
        )

    def cancel_journey(self):
        """
        Stop any movement in progress and clear the target.
        """
        self.target_location = None
        self.target_object = None
        self.is_moving = False
        self.save(
            update_fields=[
                "target_location",
                "target_object_id",
                "target_content_type",
                "is_moving",
            ]
        )

    def move_to(self, new_location: Point):
        """
        Move object to new location instantly.
        """
        self.location = new_location
        self.save(update_fields=["location"])
        return

    def step_toward(self, time_delta: float = 1.0, speed_modifier: float = 1.0):
        """Move a fraction toward target based on time_delta and movement speed"""
        if not self.target_location:
            if self.is_moving:
                self.is_moving = False
                return False

        dx = self.target_location.x - self.location.x
        dy = self.target_location.y - self.location.y
        distance = (dx**2 + dy**2) ** 0.5
        max_distance = self.movement_speed * speed_modifier * time_delta

        if distance <= max_distance:
            return self.arrive()
        else:
            factor = max_distance / distance
            new_x = self.location.x + dx * factor
            new_y = self.location.y + dy * factor
            self.location = Point(new_x, new_y, srid=self.location.srid)
            if not self.is_moving:
                self.is_moving = True

        # No save here: done in move tick bulk update
        return True

    def arrive(self):
        self.location = self.target_location
        self.target_location = None
        self.is_moving = False
        # No save here: done in move tick bulk update
        return True

    def nearby_objects(self, queryset, radius: float):
        """Return objects from queryset within radius of self."""
        return (
            queryset.annotate(dist=Distance("location", self.location))
            .filter(dist__lte=radius)
            .order_by("dist")
        )


##########################################################
##### BUILDINGS
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

    parent_for_navigation = "population_centre"

    def __str__(self):
        return self.name


class InteriorSpace(models.Model):
    class SpaceUsage(models.TextChoices):
        LIVING = "living", "Living"
        SLEEPING = "sleeping", "Sleeping"
        HYGIENE = "hygiene", "Hygiene"
        COOKING = "cooking", "Cooking"
        STORAGE = "storage", "Storage"
        WORKSHOP = "workshop", "Workshop"
        ANIMALS = "animals", "Animals"
        COMMUNAL = "communal", "Communal"
        OTHER = "other", "Other"
    name = models.CharField(max_length=255)
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="interiorspaces")
    area = models.FloatField()
    usage = models.CharField(max_length=50, choices=SpaceUsage.choices)

    parent_for_navigation = "building"

    def __str__(self):
        return f"{self.name} ({self.usage})"


##########################################################
##### POPULATION CENTRES
##########################################################


class PopulationCentre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    location = gis_models.PointField(srid=3857, default=Point(0, 0, srid=3857))
    boundary = gis_models.PolygonField(null=True, blank=True, srid=3857)

    parent_for_navigation = None

    def __str__(self):
        return self.name

    @property
    def building_count(self):
        return self.buildings.count()

