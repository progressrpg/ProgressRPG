from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.db import models, transaction
from django.utils import timezone
from math import sqrt

from .tasks import move_characters_tick
from .utils import relative_distance_direction

##########################################################
##### MOVABLE OBJECTS/BEINGS
##########################################################


def find_path(start_node, end_node):
    # very dumb: pick first outgoing path until we reach the end
    # or you can implement BFS for shortest segment count
    visited = set()
    queue = [(start_node, [start_node])]

    while queue:
        node, path = queue.pop(0)
        if node == end_node:
            return path
        visited.add(node)
        for neighbor in node.neighbours():
            if neighbor not in visited:
                queue.append((neighbor, path + [neighbor]))
    return None


class Movable(models.Model):
    movement_speed = models.FloatField(default=1.0)
    location = gis_models.PointField(srid=3857, default=Point(0, 0, srid=3857))
    is_moving = models.BooleanField(default=False)

    current_node = models.ForeignKey(
        "locations.Node",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movables_here",
    )

    target_node = models.ForeignKey(
        "locations.Node",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movables_targeting",
    )

    # LEGACY - Generic FKs
    current_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_movables",
    )
    current_object_id = models.PositiveIntegerField(null=True, blank=True)
    current_object = GenericForeignKey("current_content_type", "current_object_id")

    @property
    def current_building(self):
        return self.current_node.building if self.current_node else None

    @property
    def is_inside(self):
        return bool(self.current_node and self.current_node.building)

    class Meta:
        abstract = True

    def set_destination(self, *, node=None, obj=None, point=None):
        """
        Assign a destination by resolving to a target Node and creating a Journey.
        """

        # ---- Resolve target_node ----

        if node is not None:
            target_node = node

        elif obj is not None:
            # Prefer explicit node relationship if you add one later
            target_node = Node.objects.filter(building=obj).get()
            # ^ .get() on purpose: wrong data should explode

        elif point is not None:
            target_node = (
                Node.objects.annotate(distance=Distance("location", point))
                .order_by("distance")
                .first()
            )

        else:
            raise ValueError("Must provide node, obj, or point")

        if not target_node:
            raise ValueError("Could not resolve target node")

        # ---- Pathfinding ----

        if not self.current_node:
            raise ValueError("Movable has no current_node")

        path = find_path(self.current_node, target_node)
        if not path:
            raise ValueError(f"No path found from {self.current_node} to {target_node}")

        Journey.objects.create(
            character=self,
            start_node=self.current_node,
            destination_node=target_node,
            path_nodes=[node.pk for node in path],
            current_index=0,
        )

        self.is_moving = True
        self.save(update_fields=["is_moving"])

        from character.models import Character

        with transaction.atomic():
            Character.objects.select_for_update().filter(is_moving=True)
            moving_count = Character.objects.filter(is_moving=True).count()

        if moving_count == 1:
            move_characters_tick.apply_async()

    def move_to(self, new_node: "locations.Node"):
        """
        Move object to new node instantly.
        """
        self.current_node = new_node
        self.location = new_node.location
        self.is_moving = False
        self.save(update_fields=["current_node", "location", "is_moving"])
        return

    def step_toward(self, time_delta: float = 1.0, speed_modifier: float = 1.0):
        """Move along the current journey toward the next node."""

        if not self.journey or self.journey.is_complete():
            if self.is_moving:
                self.is_moving = False
            return False

        # Determine the next target node
        next_node = self.journey.next_node()
        if not next_node:
            # Reached end of journey
            self.is_moving = False
            return self.arrive()  # optional: triggers whatever arrive() does
            if not self.target_location:
                if self.is_moving:
                    self.is_moving = False
                    return False

        dx = next_node.location.x - self.location.x
        dy = next_node.location.y - self.location.y
        distance = (dx**2 + dy**2) ** 0.5
        max_distance = self.movement_speed * speed_modifier * time_delta

        if distance <= max_distance:
            # Arrive at node
            self.location = Point(
                next_node.location.x, next_node.location.y, srid=self.location.srid
            )
            self.journey.advance_index()  # move to next node in path
            if self.journey.is_complete():
                self.is_moving = False
                return self.arrive()
        else:
            # Move partway toward next node
            factor = max_distance / distance
            new_x = self.location.x + dx * factor
            new_y = self.location.y + dy * factor
            self.location = Point(new_x, new_y, srid=self.location.srid)
            if not self.is_moving:
                self.is_moving = True

        # No save here: done in move tick bulk update
        return True

    def arrive(self):
        """
        Called when the Movable reaches the final node of its Journey.
        Finalises the Journey and updates semantic location state.
        """
        journey = self.journey
        if not journey:
            return False

        final_node = journey.destination_node

        # Snap to node
        self.location = final_node.location

        # Update semantic "where am I?"
        if final_node.building:
            self.current_object = final_node.building
            self.current_content_type = ContentType.objects.get_for_model(
                final_node.building
            )
            self.current_object_id = final_node.building.pk
        else:
            self.current_object = None
            self.current_content_type = None
            self.current_object_id = None

        # Finalise journey
        journey.finished_at = timezone.now()
        journey.status = "complete"
        journey.save(update_fields=["finished_at", "status"])

        self.journey = None
        self.is_moving = False

        self.save(
            update_fields=[
                "location",
                "current_content_type",
                "current_object_id",
                "is_moving",
                "journey",
            ]
        )

        return True

    def nearby_objects(self, queryset, radius: float):
        """Return objects from queryset within radius of self."""
        return (
            queryset.annotate(dist=Distance("location", self.location))
            .filter(dist__lte=radius)
            .order_by("dist")
        )


##########################################################
##### TRAVEL
##########################################################


class Node(models.Model):
    name = models.CharField(max_length=100, blank=True)
    location = gis_models.PointField()
    population_centre = models.ForeignKey(
        "locations.PopulationCentre",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="nodes",
    )
    building = models.ForeignKey(
        "locations.Building",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="node",
    )

    def neighbours(self):
        return Node.objects.filter(paths_from__from_node=self)

    def paths(self):
        return Path.objects.filter(models.Q(from_node=self))

    def __str__(self):
        return self.name or f"Node {self.pk}"


class Path(models.Model):
    from_node = models.ForeignKey(
        Node, related_name="paths_from", on_delete=models.CASCADE
    )
    to_node = models.ForeignKey(Node, related_name="paths_to", on_delete=models.CASCADE)
    population_centre = models.ForeignKey(
        "locations.PopulationCentre",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="paths",
    )
    length = models.FloatField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.from_node_id and self.to_node_id:
            try:
                self.length = self.from_node.location.distance(self.to_node.location)
            except Exception:
                pass
        super().save(*args, **kwargs)

    def other_end(self, node):
        if node == self.from_node:
            return self.to_node
        return None

    def __str__(self):
        return f"{self.from_node} → {self.to_node}"


class Journey(models.Model):
    character = models.ForeignKey("character.Character", on_delete=models.CASCADE)
    start_node = models.ForeignKey(
        "locations.Node", related_name="journeys_started", on_delete=models.CASCADE
    )
    destination_node = models.ForeignKey(
        "locations.Node", related_name="journeys_ending", on_delete=models.CASCADE
    )

    # store the planned path as a list of node IDs
    path_nodes = models.JSONField(blank=True, null=True)

    # current position in the path
    current_index = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, default="ongoing"
    )  # e.g., ongoing, completed

    def serialize_for_client(self):
        # convert path_nodes to coordinates
        nodes = Node.objects.filter(id__in=self.path_nodes).order_by("id")
        coords = [[node.location.x, node.location.y] for node in nodes]

        segment_distances = [
            nodes[i].location.distance(nodes[i + 1].location)
            for i in range(len(nodes) - 1)
        ]

        return {
            "character_id": self.character.pk,
            "path": coords,
            "segment_distances": segment_distances,
            "current_index": self.current_index,
            "status": self.status,
        }

    def advance_node(self):
        """Move to the next node in the journey, if any."""
        if self.status != "active":
            return False

        if self.current_index < len(self.path_nodes) - 1:
            self.current_index += 1
            self.save(update_fields=["current_index"])
            return True

        self.status = "complete"
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])
        self.character.arrive()  # set final location
        return False

    def current_node(self):
        if self.path_nodes:
            node_id = self.path_nodes[self.current_index]
            return Node.objects.get(pk=node_id)
        return None

    def next_node(self):
        if self.path_nodes and self.current_index + 1 < len(self.path_nodes):
            return Node.objects.get(pk=self.path_nodes[self.current_index + 1])
        return None

    def cancel(self):
        """
        Stop any movement in progress and clear the target.
        """
        self.status = "complete"
        self.is_moving = False
        self.save(update_fields=["status"])


##########################################################
##### BUILDINGS
##########################################################


class Building(models.Model):
    BUILDING_TYPES = [
        ("residential", "Residential"),
        ("granary", "Granary"),
        ("inn", "Inn"),
        ("mill", "Mill"),
        ("bakery", "Bakery"),
        ("communal", "Communal"),
    ]

    name = models.CharField(max_length=255, unique=True)
    building_type = models.CharField(
        max_length=50, choices=BUILDING_TYPES, default="residential"
    )
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
        return f"{self.name} ({self.building_type})"


class InteriorSpace(models.Model):
    class SpaceUsage(models.TextChoices):
        LIVING = "living", "Living"
        SLEEPING = "sleeping", "Sleeping"
        HYGIENE = "hygiene", "Hygiene"
        KITCHEN = "kitchen", "Kitchen"
        STORAGE = "storage", "Storage"
        WORKSHOP = "workshop", "Workshop"
        ANIMALS = "animals", "Animals"
        MEETING = "meeting", "Meeting"
        OTHER = "other", "Other"
    name = models.CharField(max_length=255)
    building = models.ForeignKey(
        Building, on_delete=models.CASCADE, related_name="interiorspaces"
    )
    location = gis_models.PointField(srid=3857, null=True, blank=True)
    area = models.FloatField()
    usage = models.CharField(max_length=50, choices=SpaceUsage.choices)

    parent_for_navigation = "building"

    def __str__(self):
        return f"{self.name} ({self.usage})"


##########################################################
##### LAND USE
##########################################################


class LandArea(models.Model):
    """
    A named geographic region around a settlement.
    This is not property. It is a communal or functional area.
    Size in hectares.
    """

    name = models.CharField(max_length=255)
    population_centre = models.ForeignKey(
        "locations.PopulationCentre",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="land_areas",
    )

    location = gis_models.PointField(srid=3857, null=True, blank=True)
    boundary = gis_models.PolygonField(srid=3857, null=True, blank=True)
    size = models.FloatField(help_text="Size of land area in hectares")

    parent_for_navigation = "population_centre"

    def __str__(self):
        return f"{self.name} ({self.size:.1f} ha)"


class Subzone(models.Model):
    """
    Subdivisions with usage choice.
    Size in hectares.
    """

    land_area = models.ForeignKey(
        LandArea, on_delete=models.CASCADE, related_name="subzones"
    )
    name = models.CharField(max_length=255)
    location = gis_models.PointField(srid=3857, null=True, blank=True)
    boundary = gis_models.PolygonField(srid=3857, null=True, blank=True)
    size = models.FloatField(help_text="Size of subzone in hectares")

    # Optional "intended usage", not exclusive or enforced.
    usage = models.CharField(
        max_length=50,
        choices=[
            ("crops", "Crop Growing"),
            ("grazing", "Grazing Land"),
            ("foraging", "Foraging"),
            ("woodland", "Woodland"),
            ("orchard", "Orchard"),
            ("other", "Other"),
        ],
        default="crops",
    )

    parent_for_navigation = "land_area"

    def __str__(self):
        return f"{self.usage} ({self.size:.1f} ha)"


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

    def relative_to_centre(self, obj):
        return relative_distance_direction(self.location, obj.location)
