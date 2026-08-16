from rest_framework import serializers
from character.models import CharacterLocation
from character.serializers import CharacterSerializer
from character.services import relationship_services
from economy.constants import format_quantity

from locations.models import (
    InteriorSpace,
    Building,
    PopulationCentre,
    LandArea,
    Subzone,
    Node,
    Path,
    Road,
    Journey,
)
from locations.services import population_estimation

##########################################################
##### LOCATION SERIALISERS
##########################################################


class GeoJSONFeatureSerializer(serializers.Serializer):
    """
    Base helper: subclasses implement get_geometry() and get_properties().
    """

    feature_type: str | None = None  # optional string, e.g. "building", "path"

    def get_geometry(self, obj):
        raise NotImplementedError

    def get_properties(self, obj):
        return {}

    def to_representation(self, obj):
        props = {
            **self.get_properties(obj),
        }
        if self.feature_type and "feature_type" not in props:
            props["feature_type"] = self.feature_type

        return {
            "type": "Feature",
            "geometry": self.get_geometry(obj),
            "properties": props,
        }


class PointFeatureSerializer(GeoJSONFeatureSerializer):
    feature_type = "point"

    def get_geometry(self, obj):
        return {
            "type": "Point",
            "coordinates": [float(obj.location.x), float(obj.location.y)],
        }

    def get_properties(self, obj):
        return {
            "id": obj.id,
            "name": getattr(obj, "name", ""),
        }


class PopulationCentreLabelFeatureSerializer(PointFeatureSerializer):
    feature_type = "population_centre_label"

    def get_properties(self, obj):
        return {
            "name": obj.name,
            "population_centre_id": obj.id,
            "progress": obj.progress,
            "state": obj.state,
        }


# Cap on how many upcoming path nodes a moving character's map feature
# carries per poll, rather than its full remaining route. Keeps response
# size bounded independent of how many villages a future multi-village map
# response might cover (see .claude/plans/issue-615-path-aware-movement-
# interpolation-plan.md) - the frontend just re-extends the preview on the
# following poll as the character advances, so this only needs to comfortably
# cover the distance travelled in one poll interval, not the whole journey.
JOURNEY_PATH_PREVIEW_LIMIT = 10


class CharacterPointFeatureSerializer(PointFeatureSerializer):
    feature_type = "character"

    def get_point(self, obj):
        return obj.location.x, obj.location.y

    def _primary_location_type(self, obj, role):
        # Building.name is a bookkeeping string (e.g. "House 2 of (Driftmoor
        # village)" - see BuildingFeatureSerializer's docstring), not meant
        # for display; building_type is what the frontend maps to a plain
        # label ("House", "Bakery", ...) for the building's own tooltip
        # (BUILDING_TYPE_LABELS in geojson.tsx) - exposing it here instead of
        # the name keeps a character's home/work tooltip consistent with
        # that.
        for location in obj.locations.all():
            if location.role == role and location.is_primary:
                return location.location.building_type
        return None

    def _primary_location_id(self, obj, role):
        # The building's own pk, alongside _primary_location_type's plain
        # type label - lets the frontend cross-reference a character back
        # to its home Building (e.g. BuildingDetail's resident list, built
        # client-side by matching already-loaded character features'
        # home_id against the selected building's id - see the map entity
        # detail card).
        for location in obj.locations.all():
            if location.role == role and location.is_primary:
                return location.location_id
        return None

    def _active_journey(self, obj):
        journeys = getattr(obj, "active_journey_list", None)
        if journeys is not None:
            return journeys[0] if journeys else None
        return obj.journeys.filter(status="active").first()

    def _building_for_node(self, node):
        # Node.building and Node.interior_space are mutually exclusive (see
        # the node_building_or_interior constraint) - an indoor node (kind
        # INTERIOR) only sets interior_space, so building alone misses it.
        # InteriorSpace.building is required, so this is the full building
        # for any node the character could actually be standing at.
        if node is None:
            return None
        return node.building or (
            node.interior_space.building if node.interior_space else None
        )

    def _current_activity_name(self, obj):
        # current_activity_list is a Prefetch (see PopulationCentreMapView/
        # MapViewportView) filtered to the one CharacterActivity active right
        # now - falls back to Behaviour.get_current_activity()'s own query
        # (e.g. for a single un-prefetched character) rather than requiring
        # every caller to set it up. activity_definition.narrative is the
        # verb-phrase form for "X is ___" sentences ("delivering goods to
        # neighbours", not the label "Deliver goods to neighbours") - see
        # ActivityDefinition.narrative.
        activities = getattr(obj, "current_activity_list", None)
        if activities is not None:
            activity = activities[0] if activities else None
        else:
            activity = obj.behaviour.get_current_activity()
        return activity.narrative if activity else None

    def get_properties(self, obj):
        needs = getattr(obj, "needs", None)
        journey = self._active_journey(obj)
        path = None
        if journey is not None:
            path = [
                [float(node.location.x), float(node.location.y)]
                for node in journey.remaining_path_nodes(
                    limit=JOURNEY_PATH_PREVIEW_LIMIT
                )
            ]

        # current_building/destination building_type feed the map tooltip's
        # "[Activity] at [building]" / "Walking to [building]" copy - None
        # means the node has no building (tooltip reads "outside" instead).
        current_building = self._building_for_node(obj.current_node)
        destination_building = (
            self._building_for_node(journey.destination_node)
            if journey is not None
            else None
        )

        return {
            "id": obj.id,
            "name": obj.name,
            "home_type": self._primary_location_type(obj, CharacterLocation.Role.HOME),
            "home_id": self._primary_location_id(obj, CharacterLocation.Role.HOME),
            "work_type": self._primary_location_type(obj, CharacterLocation.Role.WORK),
            "work_id": self._primary_location_id(obj, CharacterLocation.Role.WORK),
            "hunger_label": needs.hunger_label() if needs else None,
            "current_activity": self._current_activity_name(obj),
            "is_moving": obj.is_moving,
            "effective_speed": obj.movement_speed,
            "path": path,
            "current_location_type": (
                current_building.building_type if current_building else None
            ),
            "destination_location_type": (
                destination_building.building_type if destination_building else None
            ),
        }


class CharacterDetailSerializer(serializers.Serializer):
    """
    Richer, on-demand character info for the map's detail card (see
    MapCharacterDetailView) - starts from the same tooltip-level properties
    CharacterPointFeatureSerializer already computes (home/work/activity/
    is_moving), then adds age/sex/relationships. Those involve extra
    queries per character, so they're deliberately kept out of the bulk
    per-poll map feature every character on screen carries, and only
    fetched once a player actually opens that one character's detail card.
    """

    def to_representation(self, obj):
        properties = CharacterPointFeatureSerializer().get_properties(obj)
        properties["age"] = int(obj.get_age() // 365)
        properties["sex"] = obj.sex
        properties["relationships"] = [
            {
                "character_id": member["character"].id,
                "name": member["character"].name,
                "label": relationship_services.household_relationship_label(
                    member["relationship_type"],
                    member["other_role"],
                    member["character"].sex,
                ),
            }
            for member in relationship_services.relationship_get_household_members(obj)
        ]
        return properties


class LineStringFeatureSerializer(GeoJSONFeatureSerializer):
    feature_type = "line"

    def get_geometry(self, obj):
        return {
            "type": "LineString",
            "coordinates": [
                [float(obj.from_node.location.x), float(obj.from_node.location.y)],
                [float(obj.to_node.location.x), float(obj.to_node.location.y)],
            ],
        }

    def get_properties(self, obj):
        return {
            "id": obj.id,
            "name": getattr(obj, "name", ""),
        }


class PathFeatureSerializer(LineStringFeatureSerializer):
    feature_type = "path"

    def get_geometry(self, obj):
        # Use the stored geom (which may include a waypoint inserted by
        # generate_paths to route around a building - issue #656) rather
        # than always drawing a straight line between the two endpoints.
        if obj.geom is not None:
            return {
                "type": "LineString",
                "coordinates": [[float(x), float(y)] for x, y in obj.geom.coords],
            }
        return super().get_geometry(obj)

    def get_properties(self, obj):
        return {
            "id": obj.id,
            "name": getattr(obj, "name", ""),
        }


class RoadFeatureSerializer(GeoJSONFeatureSerializer):
    """
    Renders a Road's own `geom` LineString directly - unlike
    PathFeatureSerializer, which draws a straight line between two Node
    locations, a Road's geometry is the actual (possibly multi-vertex)
    imported polyline.
    """

    feature_type = "road"

    def get_geometry(self, obj):
        return {
            "type": "LineString",
            "coordinates": [[float(x), float(y)] for x, y in obj.geom.coords],
        }

    def get_properties(self, obj):
        return {
            "id": obj.id,
            "name": obj.name,
            "width": obj.width,
        }


class PolygonFeatureSerializer(GeoJSONFeatureSerializer):
    feature_type = "polygon"

    polygon_attr: str | None = None  # e.g. "footprint" or "boundary"

    def get_geometry(self, obj):
        assert self.polygon_attr is not None
        geom = getattr(obj, self.polygon_attr)
        outer_ring = geom.coords[0]
        coords = [[list(map(float, pt)) for pt in outer_ring]]
        return {"type": "Polygon", "coordinates": coords}

    def get_properties(self, obj):
        return {
            "id": getattr(obj, "id", None),
            "name": getattr(obj, "name", ""),
        }


class BuildingFeatureSerializer(PolygonFeatureSerializer):
    feature_type = "building"
    polygon_attr = "footprint"

    def _primary_count(self, obj, role):
        return sum(
            1
            for location in obj.character_locations.all()
            if location.role == role and location.is_primary
        )

    def get_properties(self, obj):
        goods = [
            {
                "good_type": stock.good_type,
                "display": format_quantity(stock.good_type, stock.quantity),
            }
            for stock in obj.goods_stocks.all()
            if stock.quantity > 0
        ]
        return {
            "id": obj.id,
            "name": obj.name,
            "building_type": obj.building_type,
            "workers": self._primary_count(obj, CharacterLocation.Role.WORK),
            "residents": self._primary_count(obj, CharacterLocation.Role.HOME),
            # 0 (never None) for a non-residential building - same "not
            # applicable" shape residents/workers already use above, rather
            # than the frontend needing to special-case null vs. zero.
            "residential_capacity": population_estimation.residential_capacity(obj),
            "goods": goods,
        }


class BoundaryFeatureSerializer(PolygonFeatureSerializer):
    feature_type = "boundary"
    polygon_attr = "boundary"

    def get_properties(self, obj):
        return {"feature_type": "boundary", "name": obj.name}


class SubzoneFeatureSerializer(PolygonFeatureSerializer):
    feature_type = "subzone"
    polygon_attr = "boundary"

    def get_properties(self, obj):
        crop = getattr(obj, "field_crop", None)
        return {
            "id": obj.id,
            "name": obj.name,
            "usage": obj.usage,
            "crop_stage": crop.stage if crop else None,
            "crop_progress": crop.growth_progress if crop else None,
            # Lets the frontend scatter a field_shelter's idle workers across
            # the crops Subzone(s) it serves instead of clustering them at the
            # shelter's own (small, standalone) footprint - see
            # generate_fields.py, which groups every crops Subzone in a
            # population centre around one shared shelter Building.
            "shelter_building_id": crop.shelter_building_id if crop else None,
        }


class FeatureCollectionSerializer(serializers.Serializer):
    """
    Wraps a list of GeoJSON Feature dicts into a GeoJSON FeatureCollection.

    Usage:
        features = [...]
        data = FeatureCollectionSerializer.from_features(features, bbox=[...], meta={...}).data
    """

    type = serializers.CharField(default="FeatureCollection")
    features = serializers.ListField(child=serializers.DictField())
    bbox = serializers.ListField(
        child=serializers.FloatField(), required=False, allow_null=True
    )
    meta = serializers.DictField(required=False)

    @classmethod
    def from_features(cls, features, *, bbox=None, meta=None):
        payload = {"features": features}
        if bbox is not None:
            payload["bbox"] = bbox
        if meta is not None:
            payload["meta"] = meta
        return cls(payload)

    def validate_bbox(self, value):
        # GeoJSON bbox can be [minx, miny, maxx, maxy] (2D) or include z.
        if value is None:
            return value
        if len(value) not in (4, 6):
            raise serializers.ValidationError("bbox must be length 4 or 6")
        return value


class InteriorSpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = InteriorSpace
        fields = "__all__"


class BuildingSerializer(serializers.ModelSerializer):
    population_centre_id = serializers.IntegerField(
        source="population_centre.id", read_only=True
    )

    class Meta:
        model = Building
        fields = [
            "id",
            "name",
            "description",
            "population_centre_id",
            "building_type",
        ]


class PopulationCentreSerializer(serializers.ModelSerializer):
    village_points = serializers.IntegerField(read_only=True)
    progress = serializers.IntegerField(read_only=True)
    state = serializers.CharField(read_only=True)
    location = serializers.SerializerMethodField()

    residents = CharacterSerializer(many=True, read_only=True)
    buildings = BuildingSerializer(many=True, read_only=True)

    class Meta:
        model = PopulationCentre
        fields = [
            "id",
            "name",
            "description",
            "location",
            "village_points",
            "progress",
            "state",
            "residents",
            "buildings",
        ]

    def get_location(self, obj):
        return [obj.location.x, obj.location.y]


class LandAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandArea
        fields = "__all__"


class SubzoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subzone
        fields = "__all__"


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = "__all__"


class PathSerializer(serializers.ModelSerializer):
    class Meta:
        model = Path
        fields = "__all__"


class RoadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Road
        fields = "__all__"


class JourneySerializer(serializers.ModelSerializer):
    path = serializers.SerializerMethodField()
    segment_distances = serializers.SerializerMethodField()
    character_name = serializers.CharField(source="character.name", read_only=True)

    class Meta:
        model = Journey
        fields = [
            "id",
            "character_id",
            "character_name",
            "path",
            "segment_distances",
            "current_index",
            "status",
        ]

    def get_path(self, obj):
        """
        Returns a list of [x, y] coordinates for all nodes in the journey.
        """
        nodes = self._get_nodes_in_path_order(obj)
        return [[float(node.location.x), float(node.location.y)] for node in nodes]

    def get_segment_distances(self, obj):
        """
        Returns a list of distances between consecutive nodes.
        """
        nodes = self._get_nodes_in_path_order(obj)
        distances = []
        for i in range(len(nodes) - 1):
            distances.append(nodes[i].location.distance(nodes[i + 1].location))
        return distances

    def _get_nodes_in_path_order(self, obj):
        nodes = Node.objects.in_bulk(obj.path_nodes)
        return [nodes[nid] for nid in obj.path_nodes if nid in nodes]
