from datetime import datetime
from character.models import Character


def is_night():
    now = datetime.now().hour
    return now < 6 or now > 20


def send_characters_inside():
    """Move characters to their sleeping interior space if it is night."""
    if not is_night():
        return

    chars_moved = []

    for char in Character.objects.all():
        home_building = char.building
        if not home_building:
            continue

        bedrooms = home_building.interiorspaces.filter(usage="sleeping")
        if not bedrooms.exists():
            continue

        room = bedrooms.order_by("?").first()
        char.set_destination(room)
        chars_moved.append(char)

    return chars_moved
