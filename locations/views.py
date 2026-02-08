from pyexpat import features
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from locations.models import (
    InteriorSpace,
    Building,
    PopulationCentre,
    LandArea,
    Subzone,
    Path,
    Journey,
)

from .serializers import (
    InteriorSpaceSerializer,
    BuildingSerializer,
    PopulationCentreSerializer,
    LandAreaSerializer,
    SubzoneSerializer,
    JourneySerializer,
    LineStringFeatureSerializer,
    PathFeatureSerializer,
    PolygonFeatureSerializer,
    PointFeatureSerializer,
    BoundaryFeatureSerializer,
    FeatureCollectionSerializer,
    CharacterPointFeatureSerializer,
    BuildingFeatureSerializer,
)

##########################################################
##### LOCATION VIEWS AND VIEWSETS
##########################################################


class PopulationCentreMapView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        population_centre = get_object_or_404(PopulationCentre, pk=pk)
        buildings = population_centre.buildings.all()

        paths = (
            population_centre.paths.all()
            .select_related("from_node", "to_node")
            .only(
                "id",
                "from_node__location",
                "to_node__location",
            )
        )
        characters = population_centre.residents.only(
            "id", "first_name", "last_name", "location"
        )

        features = []
        features.append(BoundaryFeatureSerializer(population_centre).data)
        features.extend(CharacterPointFeatureSerializer(characters, many=True).data)
        features.extend(BuildingFeatureSerializer(buildings, many=True).data)
        features.extend(PathFeatureSerializer(paths, many=True).data)

        bbox = list(population_centre.boundary.extent)
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


class PopulationCentreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PopulationCentre.objects.all()
    serializer_class = PopulationCentreSerializer


class LandAreaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LandArea.objects.all()
    serializer_class = LandAreaSerializer


class SubzoneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Subzone.objects.all()
    serializer_class = SubzoneSerializer
