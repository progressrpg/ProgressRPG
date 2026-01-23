from django.shortcuts import render
from rest_framework import viewsets
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
    LineFeatureSerializer,
)

##########################################################
##### LOCATION VIEWS AND VIEWSETS
##########################################################


from .models import PopulationCentre
from .serializers import (
    ObjectLocationSerializer,
    LineFeatureSerializer,
    PolygonFeatureSerializer,
    BoundaryFeatureSerializer,
)


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


class PopulationCentreMapView(APIView):
    def get(self, request, pk):
        population_centre = PopulationCentre.objects.get(pk=pk)
        buildings = population_centre.buildings.all()
        paths = population_centre.paths.all()
        characters = population_centre.residents.all()

        features = []

        features.append(BoundaryFeatureSerializer(population_centre).data)

        character_features = ObjectLocationSerializer(characters, many=True).data
        features.extend(character_features)

        building_features = PolygonFeatureSerializer(buildings, many=True).data
        features.extend(building_features)

        path_features = LineFeatureSerializer(paths, many=True).data
        features.extend(path_features)

        return Response(
            {
                "type": "FeatureCollection",
                "features": features,
            }
        )


class JourneyViewSet(viewsets.ViewSet):
    def list(self, request):
        journeys = Journey.objects.filter(status="active")
        serializer = JourneySerializer(journeys, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        journey = Journey.objects.get(pk=pk)
        serializer = JourneySerializer(journey)
        return Response(serializer.data)
