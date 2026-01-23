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


class ObjectLocationSerializer(serializers.Serializer):
    x = serializers.FloatField()
    y = serializers.FloatField()

    def to_representation(self, obj):
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [obj.location.x, obj.location.y],
            },
            "properties": {
                "id": obj.id,
                "name": getattr(obj, "name", ""),
            },
        }


class LineFeatureSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(required=False, default="")
    coords = serializers.SerializerMethodField()

    def get_coords(self, obj):
        """
        Returns a list of coordinate pairs for the line.
        Assumes obj has `from_node` and `to_node` with `location` attributes.
        """
        return [
            [float(obj.from_node.location.x), float(obj.from_node.location.y)],
            [float(obj.to_node.location.x), float(obj.to_node.location.y)],
        ]

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        coords = rep.pop("coords")

        return {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords,
            },
            "properties": rep,
        }


class PolygonFeatureSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    coords = serializers.SerializerMethodField()
    name = serializers.CharField()

    def get_coords(self, obj):
        # Returns list of linear rings
        # obj.footprint.coords gives outer ring only unless you use holes
        outer_ring = obj.footprint.coords[0]
        return [[list(map(float, point)) for point in outer_ring]]

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        coords = rep.pop("coords")

        return {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": coords},
            "properties": rep,
        }


class BoundaryFeatureSerializer(serializers.Serializer):
    coords = serializers.SerializerMethodField()

    def get_coords(self, obj):
        outer_ring = obj.boundary.coords[0]
        return [[list(map(float, point)) for point in outer_ring]]

    def to_representation(self, obj):
        coords = self.get_coords(obj)
        return {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": coords},
            "properties": {"type": "boundary"},
        }


class InteriorSpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = InteriorSpace
        fields = "__all__"


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = "__all__"


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
        nodes = Node.objects.filter(id__in=obj.path_nodes).order_by("id")
        return [[float(node.location.x), float(node.location.y)] for node in nodes]

    def get_segment_distances(self, obj):
        """
        Returns a list of distances between consecutive nodes.
        """
        nodes = Node.objects.filter(id__in=obj.path_nodes).order_by("id")
        distances = []
        for i in range(len(nodes) - 1):
            distances.append(nodes[i].location.distance(nodes[i + 1].location))
        return distances
