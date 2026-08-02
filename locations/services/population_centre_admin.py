from django.contrib.gis.geos import Point

from locations.models import PopulationCentre


def delete_population_centre(name: str) -> Point | None:
    """
    Delete the PopulationCentre called `name`, if one exists, and everything
    inside it, returning its old location (or None if there was nothing to
    delete).

    Building.population_centre and LandArea.population_centre are both
    SET_NULL rather than CASCADE, so deleting the centre directly would
    orphan its buildings (and their Nodes) and its land areas (and their
    cascading Subzones/FieldCrops) instead of removing them - both are
    deleted explicitly first.
    """
    try:
        existing = PopulationCentre.objects.get(name=name)
    except PopulationCentre.DoesNotExist:
        return None

    old_location = existing.location
    existing.buildings.all().delete()
    existing.land_areas.all().delete()
    existing.delete()
    return old_location
