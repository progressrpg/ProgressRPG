from rest_framework import serializers
from locations.models import (
    InteriorSpace,
    Building,
    PopulationCentre,
    LandArea,
    Subzone,
    Node,
    Path,
    Journey,
)

##########################################################
##### LOCATION SERIALISERS
##########################################################


class GeoJSONFeatureSerializer(serializers.Serializer):
    """
    Base helper: subclasses implement get_geometry() and get_properties().
    """

    feature_type = None  # optional string, e.g. "building", "path"

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


class CharacterPointFeatureSerializer(PointFeatureSerializer):
    feature_type = "character"

    def get_point(self, obj):
        return obj.location.x, obj.location.y

    def get_properties(self, obj):
        return {
            "id": obj.id,
            "name": obj.name,
        }


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

    def get_properties(self, obj):
        return {
            "id": obj.id,
            "name": getattr(obj, "name", ""),
        }


class PolygonFeatureSerializer(GeoJSONFeatureSerializer):
    feature_type = "polygon"

    polygon_attr = None  # e.g. "footprint" or "boundary"

    def get_geometry(self, obj):
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

    def get_properties(self, obj):
        return {
            "id": obj.id,
            "name": obj.name,
            "building_type": obj.building_type,
        }


class BoundaryFeatureSerializer(PolygonFeatureSerializer):
    feature_type = "boundary"
    polygon_attr = "boundary"

    def get_properties(self, obj):
        return {"feature_type": "boundary"}


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
    class Meta:
        model = Building
        fields = [
            "id",
            "name",
            "population_centre_id",
            "node_id",
            "interior_space_id",
            "building_type",
        ]


class PopulationCentreSerializer(serializers.ModelSerializer):
    class Meta:
        model = PopulationCentre
        fields = "__all__"


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
