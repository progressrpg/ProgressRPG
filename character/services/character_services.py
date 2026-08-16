from __future__ import annotations


def character_react_to_sun_phase(character, phase: str) -> None:
    if phase == "dawn":
        print(f"{character.name} wakes up and moves outside")
        character.go_outside(radius=10)
    elif phase == "day":
        print(f"{character.name} is outside during the day")
    elif phase == "dusk":
        print(f"{character.name} heads inside for the night")
        character.go_home()
    elif phase == "night":
        print(f"{character.name} is indoors at night")


def character_assign_home(character, building) -> None:
    from character.models import CharacterLocation

    character.population_centre = building.population_centre
    character.save(update_fields=["population_centre"])

    CharacterLocation.objects.update_or_create(
        character=character,
        role=CharacterLocation.Role.HOME,
        is_primary=True,
        defaults={"location": building},
    )


def character_assign_work(character, building) -> None:
    from character.models import CharacterLocation

    CharacterLocation.objects.update_or_create(
        character=character,
        role=CharacterLocation.Role.WORK,
        is_primary=True,
        defaults={"location": building},
    )


def character_has_available(model_cls) -> bool:
    return model_cls.objects.linkable().exists()
