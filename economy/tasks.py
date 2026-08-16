import logging

from celery import shared_task
from django.utils import timezone

from .constants import (
    BREAD_PER_CHARACTER_DAILY_CONSUMPTION,
    FLOUR_BUFFER_DAYS,
    FLOUR_TO_BREAD_RATIO,
    GROWTH_DURATION,
    HUNGER_MAX,
    HUNGER_PER_MISSED_MEAL,
    PER_WORKER_DAILY_BAKING_CAPACITY,
    PER_WORKER_DAILY_CAPACITY,
    PER_WORKER_DAILY_MILLING_CAPACITY,
    SOWING_WINDOW_MONTHS,
    WHEAT_TO_FLOUR_RATIO,
    YIELD_PER_AREA,
)
from .conversion import convert_goods
from .models import FieldCrop, GoodsConversionState, GoodsStock
from .services.capacity_services import (
    daily_bread_demand,
    daily_flour_demand,
    find_bakery,
    find_granary,
    find_mill,
    worker_capacity_present,
)
from locations.models import Building

logger = logging.getLogger("general")


@shared_task
def advance_field_economy_tick(today=None, now=None):
    """
    Daily economy step, run once shortly after the work shift ends: advance
    each FieldCrop's growth cycle one stage, and if ready, harvest capped by
    how many workers are physically present at its field_shelter.
    """
    today = today or timezone.localdate()
    now = now or timezone.now()

    for crop in FieldCrop.objects.select_related(
        "subzone", "shelter_building", "shelter_building__population_centre"
    ):
        if crop.last_processed_on == today:
            continue

        if crop.stage == FieldCrop.Stage.FALLOW:
            _replant(crop, today, now)
        elif crop.stage == FieldCrop.Stage.GROWING:
            _maybe_ripen(crop, now)
        elif crop.stage == FieldCrop.Stage.READY:
            _harvest(crop)

        crop.last_processed_on = today
        crop.save(
            update_fields=[
                "stage",
                "planted_at",
                "ready_yield",
                "harvested_amount",
                "last_processed_on",
            ]
        )


def _replant(crop, today, now):
    # Spring wheat has a real sowing window - a field harvested in August
    # can't be replanted again until next spring, so it just stays fallow
    # until the window comes back around.
    if today.month not in SOWING_WINDOW_MONTHS:
        return

    crop.planted_at = now
    crop.stage = FieldCrop.Stage.GROWING


def _maybe_ripen(crop, now):
    if crop.planted_at is None:
        crop.planted_at = now
        return

    if now - crop.planted_at < GROWTH_DURATION:
        return

    # Wheat is a weight-kind good (whole grams, see GOOD_TYPE_UNIT) - no
    # meaningful sub-gram precision, so round the area-derived yield.
    crop.ready_yield = round(crop.subzone.boundary.area * YIELD_PER_AREA)
    crop.harvested_amount = 0
    crop.stage = FieldCrop.Stage.READY


def _harvest(crop):
    remaining = crop.ready_yield - crop.harvested_amount
    if remaining <= 0:
        crop.stage = FieldCrop.Stage.FALLOW
        return

    present = worker_capacity_present(crop.shelter_building)
    today_yield = min(remaining, present * PER_WORKER_DAILY_CAPACITY)
    if today_yield <= 0:
        return

    _deposit_into_granary(crop.shelter_building, today_yield)

    crop.harvested_amount += today_yield
    if crop.harvested_amount >= crop.ready_yield:
        crop.stage = FieldCrop.Stage.FALLOW


def _deposit_into_granary(shelter_building, amount):
    population_centre = shelter_building.population_centre
    if population_centre is None:
        logger.warning(
            "FieldCrop harvest for shelter %s has no population centre - " "wheat lost",
            shelter_building.id,
        )
        return

    granary = find_granary(population_centre)
    if granary is None:
        logger.warning(
            "No granary in %s - harvested wheat lost", population_centre.name
        )
        return

    stock, _ = GoodsStock.objects.get_or_create(
        building=granary, good_type=GoodsStock.GoodType.WHEAT
    )
    deposit = min(amount, max(0.0, stock.capacity - stock.quantity))
    if deposit <= 0:
        return

    stock.quantity += deposit
    stock.save(update_fields=["quantity"])


@shared_task
def advance_mill_economy_tick(today=None):
    """
    Daily economy step: each mill converts granary wheat into flour stored
    at itself, capped by how many workers are physically present at the
    mill (same "must actually show up" premise as the field harvest),
    storage capacity, and FLOUR_BUFFER_DAYS' worth of flour demand - flour
    keeps (unlike bread, see advance_bakery_economy_tick), so it's fine to
    mill a buffer ahead rather than only a day's worth.
    """
    today = today or timezone.localdate()

    for mill in Building.objects.filter(
        capabilities__activity="milling"
    ).select_related("population_centre"):
        state, _ = GoodsConversionState.objects.get_or_create(
            building=mill, activity="milling"
        )
        if state.last_processed_on == today:
            continue

        granary = find_granary(mill.population_centre)
        if granary is not None:
            present = worker_capacity_present(mill)
            flour_buffer_target = (
                daily_flour_demand(mill.population_centre) * FLOUR_BUFFER_DAYS
            )
            flour_stock = GoodsStock.objects.filter(
                building=mill, good_type=GoodsStock.GoodType.FLOUR
            ).first()
            current_flour = flour_stock.quantity if flour_stock else 0
            mill_target = max(0.0, flour_buffer_target - current_flour)

            convert_goods(
                granary,
                mill,
                input_good=GoodsStock.GoodType.WHEAT,
                output_good=GoodsStock.GoodType.FLOUR,
                workers_present=present,
                per_worker_capacity=PER_WORKER_DAILY_MILLING_CAPACITY,
                conversion_ratio=WHEAT_TO_FLOUR_RATIO,
                max_output=mill_target,
            )
        else:
            logger.warning(
                "No granary for mill %s (%s) - nothing to mill",
                mill.id,
                mill.population_centre,
            )

        state.last_processed_on = today
        state.save(update_fields=["last_processed_on"])


@shared_task
def advance_bakery_economy_tick(today=None):
    """
    Daily economy step: each bakery converts mill flour into bread stored
    at itself, capped by how many workers are physically present at the
    bakery (same premise as milling), and by today's expected consumption -
    bread goes stale, so a bakery only bakes enough to cover its village's
    daily demand rather than baking up to its full storage/labor limit.
    """
    today = today or timezone.localdate()

    for bakery in Building.objects.filter(
        capabilities__activity="baking"
    ).select_related("population_centre"):
        state, _ = GoodsConversionState.objects.get_or_create(
            building=bakery, activity="baking"
        )
        if state.last_processed_on == today:
            continue

        mill = find_mill(bakery.population_centre)
        if mill is not None:
            present = worker_capacity_present(bakery)
            demand = daily_bread_demand(bakery.population_centre)
            bread_stock = GoodsStock.objects.filter(
                building=bakery, good_type=GoodsStock.GoodType.BREAD
            ).first()
            current_bread = bread_stock.quantity if bread_stock else 0
            bake_target = max(0.0, demand - current_bread)

            convert_goods(
                mill,
                bakery,
                input_good=GoodsStock.GoodType.FLOUR,
                output_good=GoodsStock.GoodType.BREAD,
                workers_present=present,
                per_worker_capacity=PER_WORKER_DAILY_BAKING_CAPACITY,
                conversion_ratio=FLOUR_TO_BREAD_RATIO,
                max_output=bake_target,
            )
        else:
            logger.warning(
                "No mill for bakery %s (%s) - nothing to bake",
                bakery.id,
                bakery.population_centre,
            )

        state.last_processed_on = today
        state.save(update_fields=["last_processed_on"])


@shared_task
def advance_bread_consumption_tick(today=None):
    """
    Daily economy step: each character eats from their home population
    centre's bakery bread stock. No presence check - unlike harvesting,
    milling and baking, eating isn't labor, so it doesn't require the
    character to be standing at the bakery.
    """
    from character.models import CharacterLocation

    today = today or timezone.localdate()
    bakery_cache = {}

    homes = (
        CharacterLocation.objects.filter(
            role=CharacterLocation.Role.HOME, is_primary=True
        )
        .select_related("character__needs", "location__population_centre")
        .order_by("character_id")
    )

    for home in homes:
        character = home.character
        needs = getattr(character, "needs", None)
        if needs is None:
            continue
        if needs.last_fed_on == today:
            continue

        population_centre = home.location.population_centre
        centre_id = population_centre.id if population_centre else None
        if centre_id not in bakery_cache:
            bakery_cache[centre_id] = find_bakery(population_centre)
        bakery = bakery_cache[centre_id]

        fed = False
        if bakery is not None:
            stock, _ = GoodsStock.objects.get_or_create(
                building=bakery, good_type=GoodsStock.GoodType.BREAD
            )
            if stock.quantity >= BREAD_PER_CHARACTER_DAILY_CONSUMPTION:
                stock.quantity -= BREAD_PER_CHARACTER_DAILY_CONSUMPTION
                stock.save(update_fields=["quantity"])
                fed = True

        if fed:
            needs.hunger = max(0.0, needs.hunger - HUNGER_PER_MISSED_MEAL)
        else:
            needs.hunger = min(HUNGER_MAX, needs.hunger + HUNGER_PER_MISSED_MEAL)
            logger.warning(
                "Character %s not fed for %s - no bread available",
                character.id,
                today,
            )

        needs.last_fed_on = today
        needs.save(update_fields=["hunger", "last_fed_on"])
