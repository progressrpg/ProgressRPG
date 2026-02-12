from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from .services import movement as movement_service
from .utils import relative_distance_direction

##########################################################
##### MOVABLE OBJECTS/BEINGS
##########################################################


def find_path(start_node: "Node", end_node: "Node"):
    return movement_service.find_path(start_node, end_node)


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

    @property
    def current_building(self):
        return self.current_node.building if self.current_node else None

    @property
    def is_inside(self):
        return bool(self.current_node and self.current_node.building)

    @property
    def current_journey(self):
        return self.journeys.filter(status="active").first()

    class Meta:
        abstract = True

    def go_home(self):
        return movement_service.go_home(self)

    def get_nearby_outside_nodes(self, radius=50):
        return movement_service.get_nearby_outside_nodes(self, radius=radius)

    def pick_random_outside_node(self, radius=50):
        return movement_service.pick_random_outside_node(self, radius=radius)

    def go_outside(self, radius=100):
        return movement_service.go_outside(self, radius=radius)

    @transaction.atomic
    def set_destination(self, *, node=None, obj=None, point=None):
        return movement_service.set_destination(self, node=node, obj=obj, point=point)

    def move_to(self, new_node: "Node"):
        """
        Move object to new node instantly.
        """
        self.current_node = new_node
        self.location = new_node.location
        self.is_moving = False
        self.save(update_fields=["current_node", "location", "is_moving"])
        return

    def step_toward(self, time_delta: float = 1.0, speed_modifier: float = 1.0):
        return movement_service.step_toward(
            self, time_delta=time_delta, speed_modifier=speed_modifier
        )

    def arrive(self, journey):
        return movement_service.arrive(self, journey)

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
    location = gis_models.PointField(srid=3857, spatial_index=True)
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
        related_name="nodes",
    )
    interior_space = models.ForeignKey(
        "locations.InteriorSpace",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="nodes",
    )

    class Kind(models.TextChoices):
        CENTRE = "centre", "Centre"
        OUTSIDE = "outside", "Outside"
        BUILDING = "building", "Building"
        BUILDING_ENTRANCE = "building_entrance", "Building Entrance"
        INTERIOR = "interior", "Interior"
        POI = "poi", "Point of Interest"

    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OUTSIDE)

    @property
    def pc(self):
        if self.population_centre:
            return self.population_centre
        if self.building:
            return self.building.population_centre
        if self.interior_space:
            return self.interior_space.building.population_centre
        return None

    def paths(self):
        return Path.objects.filter(Q(from_node=self) | Q(to_node=self))

    def neighbours(self):
        return Node.objects.filter(
            Q(paths_from__to_node=self) | Q(paths_to__from_node=self)
        ).distinct()

    def __str__(self):
        return self.name or f"Node {self.pk}"

    class Meta:
        indexes = [
            models.Index(fields=["population_centre"], name="node_pc_idx"),
            models.Index(fields=["kind"], name="node_kind_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["building", "kind"],
                condition=Q(building__isnull=False),
                name="uniq_node_building_kind",
            ),
            models.CheckConstraint(
                condition=(
                    Q(building__isnull=True, interior_space__isnull=True)
                    | Q(population_centre__isnull=True)
                ),
                name="node_population_centre_xor_location",
            ),
            models.CheckConstraint(
                condition=Q(building__isnull=True) | Q(interior_space__isnull=True),
                name="node_building_or_interior",
            ),
        ]


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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["from_node", "to_node"], name="uniq_path_directed"
            )
        ]
        indexes = [
            models.Index(fields=["population_centre"]),
        ]

    def save(self, *args, **kwargs):
        if self.from_node_id and self.to_node_id:
            try:
                self.length = self.from_node.location.distance(self.to_node.location)
            except Exception:
                pass
        super().save(*args, **kwargs)

    def other_end(self, node: Node):
        if node == self.from_node:
            return self.to_node
        if node == self.to_node:
            return self.from_node
        return None

    def __str__(self):
        return f"{self.from_node} → {self.to_node}"


class Journey(models.Model):
    character = models.ForeignKey(
        "character.Character", on_delete=models.CASCADE, related_name="journeys"
    )
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
    status = models.CharField(max_length=20, default="active")  # e.g., active, complete

    @property
    def is_complete(self):
        return self.status == "complete"

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
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])

        self.character.is_moving = False
        self.character.save(update_fields=["is_moving"])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["character"],
                condition=Q(status="active"),
                name="uniq_active_journey_per_character",
            ),
        ]
        indexes = [
            models.Index(
                fields=["character", "status"], name="journey_char_status_idx"
            ),
        ]


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
        srid=3857,
        default=Point(0, 0, srid=3857),
        help_text="Centre location",
        spatial_index=True,
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

    class Meta:
        indexes = [
            models.Index(fields=["population_centre"]),
        ]


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

    @property
    def resident_count(self):
        return self.residents.count()

    @property
    def village_points(self):
        points = 0

        for resident in self.residents.all():
            for link in resident.links.all():
                points += link.link_points

        village_multiplier = 2 / (1 + self.residents.count())
        scaled_points = points * village_multiplier
        return int(scaled_points)

    @property
    def progress(self):
        points = self.village_points
        if points >= 400:
            return 100
        return points % 100

    @property
    def state(self):
        points = self.village_points
        if points < 100:
            return "Struggling"
        elif points < 200:
            return "Recovering"
        elif points < 300:
            return "Stable"
        else:
            return "Thriving"

    def relative_to_centre(self, obj):
        return relative_distance_direction(self.location, obj.location)

    def get_outside_nodes(self):
        """
        Return outside nodes in the same population centre.
        """
        return Node.objects.filter(
            population_centre=self,
            kind=Node.Kind.OUTSIDE,
        )
