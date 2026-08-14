from django.contrib.gis.db.models import Extent
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from character.models import Character
from progression.models import CharacterActivity
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
    CharacterDetailSerializer,
    CharacterPointFeatureSerializer,
    BuildingFeatureSerializer,
    SubzoneFeatureSerializer,
)

##########################################################
##### LOCATION VIEWS AND VIEWSETS
##########################################################


def _current_activity_prefetch(now=None):
    # Feeds CharacterPointFeatureSerializer._current_activity_name -
    # prefetches just the one CharacterActivity (if any) active right now
    # per character, same shape as the active_journey_list Prefetch below,
    # so the map's tooltip doesn't trigger a query per character.
    now = now or timezone.now()
    return Prefetch(
        "activities",
        queryset=CharacterActivity.objects.filter(
            scheduled_start__lte=now, scheduled_end__gt=now
        ).select_related("activity_definition"),
        to_attr="current_activity_list",
    )


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
        # "crops" drives FieldCrop growth-cycle rendering (see
        # SubzoneFeatureSerializer); "square" is purely a communal-space map
        # feature with no economy behaviour attached (see
        # watabou_import._import_squares) - both are just polygons on the
        # map, so they're queried and serialized together.
        visible_subzones = list(
            Subzone.objects.filter(
                land_area__population_centre=population_centre,
                usage__in=["crops", "square"],
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
            "needs", "current_node__building", "current_node__interior_space__building"
        ).prefetch_related(
            "locations__location",
            Prefetch(
                "journeys",
                queryset=Journey.objects.filter(status="active").select_related(
                    "destination_node__building",
                    "destination_node__interior_space__building",
                ),
                to_attr="active_journey_list",
            ),
            _current_activity_prefetch(),
        )

        features = []
        if population_centre.boundary:
            features.append(BoundaryFeatureSerializer(population_centre).data)
        features.extend(CharacterPointFeatureSerializer(characters, many=True).data)
        features.extend(BuildingFeatureSerializer(buildings, many=True).data)
        features.extend(SubzoneFeatureSerializer(visible_subzones, many=True).data)
        features.extend(PathFeatureSerializer(paths, many=True).data)
        features.extend(RoadFeatureSerializer(roads, many=True).data)

        bbox = (
            list(population_centre.boundary.extent)
            if population_centre.boundary
            else None
        )
        for polygon_obj, polygon_attr in [
            *((b, "footprint") for b in buildings),
            *((s, "boundary") for s in visible_subzones),
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


class InitialMapCentreView(APIView):
    """
    Picks which PopulationCentre the map's camera should open on and returns
    just enough to frame it there - id/name/bbox, not the full per-village
    payload (buildings/characters/roads/fields) PopulationCentreMapView
    returns. That fuller payload is unnecessary here: MapViewportView takes
    over as the source of truth within moments, once the camera's first
    "moveend" fires (see Map.tsx's initial-fit effect), so this only needs to
    get the camera pointed at the right place cheaply.

    Prefers the PopulationCentre containing the requesting player's linked
    character (see PlayerCharacterLink/Player.active_link) - the village the
    player actually cares about. Falls back to the lowest-pk PopulationCentre
    when there's no active link (e.g. player-character linking hasn't
    happened yet), same "just pick one, deterministically" behaviour used
    before per-player villages existed here.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        population_centre = None

        active_link = request.user.player.active_link
        if active_link and active_link.character.population_centre_id:
            population_centre = active_link.character.population_centre

        if population_centre is None:
            population_centre = PopulationCentre.objects.order_by("pk").first()

        if population_centre is None:
            return Response({"id": None, "name": None, "bbox": None})

        if population_centre.boundary:
            bbox = list(population_centre.boundary.extent)
        else:
            # Mirrors PopulationCentreMapView's own null-boundary guard - a
            # centre with no boundary polygon yet (e.g. in tests) still has a
            # location point to frame a small window around.
            x, y = population_centre.location.x, population_centre.location.y
            pad = WORLD_BOUNDS_PADDING_M
            bbox = [x - pad, y - pad, x + pad, y + pad]

        return Response(
            {"id": population_centre.id, "name": population_centre.name, "bbox": bbox}
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
        # See PopulationCentreMapView's matching comment - "crops" and
        # "square" are both just polygon map features, queried together.
        visible_subzones = list(
            Subzone.objects.filter(
                usage__in=["crops", "square"],
                boundary__isnull=False,
                boundary__bboverlaps=bbox,
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
            .select_related(
                "needs",
                "current_node__building",
                "current_node__interior_space__building",
            )
            .prefetch_related(
                "locations__location",
                Prefetch(
                    "journeys",
                    queryset=Journey.objects.filter(status="active").select_related(
                        "destination_node__building",
                        "destination_node__interior_space__building",
                    ),
                    to_attr="active_journey_list",
                ),
                _current_activity_prefetch(),
            )
        )

        features: list[dict] = []
        features.extend(BoundaryFeatureSerializer(population_centres, many=True).data)
        features.extend(
            PopulationCentreLabelFeatureSerializer(population_centres, many=True).data
        )

        features.extend(CharacterPointFeatureSerializer(characters, many=True).data)
        features.extend(BuildingFeatureSerializer(buildings, many=True).data)
        features.extend(SubzoneFeatureSerializer(visible_subzones, many=True).data)
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


class MapCharacterDetailView(APIView):
    """
    On-demand detail for one character's map detail card (progressive
    disclosure past its tooltip - see the frontend's DetailCard/
    CharacterDetail). Deliberately separate from PopulationCentreMapView/
    MapViewportView's bulk per-poll character features: age/sex/
    relationships involve extra queries per character, so they're only
    fetched once, when a player actually opens that one character's card,
    rather than for every character on every map poll.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        character = get_object_or_404(
            Character.objects.select_related(
                "needs",
                "current_node__building",
                "current_node__interior_space__building",
            ).prefetch_related(
                "locations__location",
                Prefetch(
                    "journeys",
                    queryset=Journey.objects.filter(status="active").select_related(
                        "destination_node__building",
                        "destination_node__interior_space__building",
                    ),
                    to_attr="active_journey_list",
                ),
                _current_activity_prefetch(),
            ),
            pk=pk,
        )
        return Response(CharacterDetailSerializer(character).data)


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
