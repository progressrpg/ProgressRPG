from django.contrib.gis.db.models import Extent
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from character.models import Character
from locations.models import (
    InteriorSpace,
    Building,
    PopulationCentre,
    LandArea,
    Subzone,
    Path,
    Road,
    Journey,
)
from locations.utils import InvalidBBoxError, WORLD_BOUNDS_PADDING_M, parse_bbox_param

from .serializers import (
    InteriorSpaceSerializer,
    BuildingSerializer,
    PopulationCentreSerializer,
    LandAreaSerializer,
    SubzoneSerializer,
    JourneySerializer,
    LineStringFeatureSerializer,
    PathFeatureSerializer,
    RoadFeatureSerializer,
    PolygonFeatureSerializer,
    PointFeatureSerializer,
    BoundaryFeatureSerializer,
    FeatureCollectionSerializer,
    PopulationCentreLabelFeatureSerializer,
    CharacterPointFeatureSerializer,
    BuildingFeatureSerializer,
    SubzoneFeatureSerializer,
)

##########################################################
##### LOCATION VIEWS AND VIEWSETS
##########################################################


class PopulationCentreMapView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FeatureCollectionSerializer

    def get(self, request, pk):
        population_centre = get_object_or_404(PopulationCentre, pk=pk)
        buildings = list(
            population_centre.buildings.all().prefetch_related(
                "character_locations", "goods_stocks"
            )
        )
        crop_subzones = list(
            Subzone.objects.filter(
                land_area__population_centre=population_centre, usage="crops"
            ).select_related("field_crop")
        )

        paths = (
            population_centre.paths.all()
            .select_related("from_node", "to_node")
            .only(
                "id",
                "from_node__location",
                "to_node__location",
            )
        )
        roads = population_centre.roads.all()
        characters = population_centre.residents.select_related(
            "needs"
        ).prefetch_related(
            "locations__location",
            Prefetch(
                "journeys",
                queryset=Journey.objects.filter(status="active"),
                to_attr="active_journey_list",
            ),
        )

        features = []
        if population_centre.boundary:
            features.append(BoundaryFeatureSerializer(population_centre).data)
        features.extend(CharacterPointFeatureSerializer(characters, many=True).data)
        features.extend(BuildingFeatureSerializer(buildings, many=True).data)
        features.extend(SubzoneFeatureSerializer(crop_subzones, many=True).data)
        features.extend(PathFeatureSerializer(paths, many=True).data)
        features.extend(RoadFeatureSerializer(roads, many=True).data)

        bbox = (
            list(population_centre.boundary.extent)
            if population_centre.boundary
            else None
        )
        for polygon_obj, polygon_attr in [
            *((b, "footprint") for b in buildings),
            *((s, "boundary") for s in crop_subzones),
            *((r, "geom") for r in roads),
        ]:
            geom = getattr(polygon_obj, polygon_attr)
            if geom is None:
                continue
            g_min_x, g_min_y, g_max_x, g_max_y = geom.extent
            if bbox is None:
                bbox = [g_min_x, g_min_y, g_max_x, g_max_y]
                continue
            bbox[0] = min(bbox[0], g_min_x)
            bbox[1] = min(bbox[1], g_min_y)
            bbox[2] = max(bbox[2], g_max_x)
            bbox[3] = max(bbox[3], g_max_y)
        meta = {
            "population_centre_id": population_centre.id,
            "feature_count": len(features),
            "population_centre_name": population_centre.name,
        }
        return Response(
            FeatureCollectionSerializer.from_features(
                features, bbox=bbox, meta=meta
            ).data
        )


class MapViewportView(APIView):
    """
    Cross-village map endpoint: returns every map feature whose geometry
    falls within a client-supplied `?bbox=minx,miny,maxx,maxy` viewport,
    rather than everything belonging to one PopulationCentre. Feeds a
    scrollable, multi-village map instead of PopulationCentreMapView's
    single-village view.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FeatureCollectionSerializer

    def get(self, request):
        try:
            bbox = parse_bbox_param(request.query_params.get("bbox"))
        except InvalidBBoxError:
            return Response({"error": "Invalid bbox parameter."}, status=400)

        population_centres = list(
            PopulationCentre.objects.filter(
                boundary__isnull=False, boundary__bboverlaps=bbox
            )
        )
        buildings = list(
            Building.objects.filter(
                footprint__isnull=False, footprint__bboverlaps=bbox
            ).prefetch_related("character_locations", "goods_stocks")
        )
        crop_subzones = list(
            Subzone.objects.filter(
                usage="crops", boundary__isnull=False, boundary__bboverlaps=bbox
            ).select_related("field_crop")
        )
        paths = (
            Path.objects.filter(geom__isnull=False, geom__bboverlaps=bbox)
            .select_related("from_node", "to_node")
            .only("id", "from_node__location", "to_node__location")
        )
        roads = Road.objects.filter(geom__bboverlaps=bbox)
        characters = (
            Character.objects.filter(location__contained=bbox)
            .select_related("needs")
            .prefetch_related(
                "locations__location",
                Prefetch(
                    "journeys",
                    queryset=Journey.objects.filter(status="active"),
                    to_attr="active_journey_list",
                ),
            )
        )

        features: list[dict] = []
        features.extend(BoundaryFeatureSerializer(population_centres, many=True).data)
        features.extend(
            PopulationCentreLabelFeatureSerializer(population_centres, many=True).data
        )

        features.extend(CharacterPointFeatureSerializer(characters, many=True).data)
        features.extend(BuildingFeatureSerializer(buildings, many=True).data)
        features.extend(SubzoneFeatureSerializer(crop_subzones, many=True).data)
        features.extend(PathFeatureSerializer(paths, many=True).data)
        features.extend(RoadFeatureSerializer(roads, many=True).data)

        meta = {
            "population_centre_count": len(population_centres),
            "feature_count": len(features),
        }
        return Response(
            FeatureCollectionSerializer.from_features(
                features, bbox=list(bbox.extent), meta=meta
            ).data
        )


class MapWorldBoundsView(APIView):
    """
    Returns a padded bounding box covering every PopulationCentre's location
    and (where present) boundary polygon - used by the frontend to derive
    MapLibre's `maxBounds`, so panning is limited to a generous area around
    the seeded world rather than being either unbounded or clamped to a
    single village.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        location_extent = PopulationCentre.objects.aggregate(Extent("location"))[
            "location__extent"
        ]
        boundary_extent = PopulationCentre.objects.filter(
            boundary__isnull=False
        ).aggregate(Extent("boundary"))["boundary__extent"]

        extents = [e for e in (location_extent, boundary_extent) if e]
        if not extents:
            return Response({"bbox": None})

        min_x = min(e[0] for e in extents) - WORLD_BOUNDS_PADDING_M
        min_y = min(e[1] for e in extents) - WORLD_BOUNDS_PADDING_M
        max_x = max(e[2] for e in extents) + WORLD_BOUNDS_PADDING_M
        max_y = max(e[3] for e in extents) + WORLD_BOUNDS_PADDING_M
        return Response({"bbox": [min_x, min_y, max_x, max_y]})


class JourneyViewSet(viewsets.ViewSet):
    def list(self, request):
        journeys = Journey.objects.filter(status="active")
        serializer = JourneySerializer(journeys, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        journey = get_object_or_404(Journey, pk=pk)
        serializer = JourneySerializer(journey)
        return Response(serializer.data)


class InteriorSpaceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InteriorSpace.objects.all()
    serializer_class = InteriorSpaceSerializer


class BuildingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer


class LandAreaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LandArea.objects.all()
    serializer_class = LandAreaSerializer


class SubzoneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Subzone.objects.all()
    serializer_class = SubzoneSerializer


class PopulationCentreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PopulationCentre.objects.all()
    serializer_class = PopulationCentreSerializer
