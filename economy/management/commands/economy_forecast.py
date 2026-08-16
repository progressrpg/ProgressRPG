import logging
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from character.models import CharacterLocation, CharacterNeeds
from economy.constants import (
    BREAD_PER_CHARACTER_DAILY_CONSUMPTION,
    FLOUR_TO_BREAD_RATIO,
    GROWTH_DURATION,
    WHEAT_TO_FLOUR_RATIO,
    YIELD_PER_AREA,
    format_quantity,
)
from economy.models import FieldCrop, GoodsStock
from economy.tasks import (
    advance_bakery_economy_tick,
    advance_bread_consumption_tick,
    advance_field_economy_tick,
    advance_mill_economy_tick,
)
from locations.models import Building, Node

# Overall wheat-to-bread yield of the full conversion chain, used for the
# quick analytic estimate printed before the simulation.
WHEAT_TO_BREAD_RATIO = WHEAT_TO_FLOUR_RATIO * FLOUR_TO_BREAD_RATIO

# Which good_type each working building type holds a GoodsStock for, per the
# conversion chain in economy/tasks.py (granary holds wheat, mill holds the
# flour it produces, bakery holds the bread it produces) - used to print
# storage capacity/fill for every working building, not just mills.
BUILDING_STORAGE_GOODS = {
    "granary": [GoodsStock.GoodType.WHEAT],
    "mill": [GoodsStock.GoodType.FLOUR],
    "bakery": [GoodsStock.GoodType.BREAD],
}


class Command(BaseCommand):
    help = (
        "Simulate the daily economy ticks forward N days (in a rolled-back "
        "transaction, unless --commit) and report wheat/flour/bread stock "
        "and character hunger trends over time - for tuning starting stock "
        "and economy constants by observation rather than guesswork."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=365,
            help="Number of days to simulate (default 365)",
        )
        parser.add_argument(
            "--start-date",
            help="Simulate starting from this date (YYYY-MM-DD), default today",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=30,
            help="Print a snapshot every N simulated days (default 30)",
        )
        parser.add_argument(
            "--seed-wheat",
            type=int,
            default=5000000,
            help="Add this much wheat (whole grams) to every granary before "
            "simulating, to test whether a given starting stock survives "
            "the ramp-up",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Persist the simulated changes instead of rolling them back",
        )

    def handle(self, *args, **options):
        if options["start_date"]:
            start = parse_date(options["start_date"])
            if start is None:
                raise CommandError(f"Invalid --start-date: {options['start_date']!r}")
        else:
            start = timezone.localdate()
        days = options["days"]
        interval = options["interval"]
        seed_wheat = options["seed_wheat"]

        self._print_analytic_estimate()

        with transaction.atomic():
            if seed_wheat:
                self._seed_wheat(seed_wheat)

            self._place_assigned_workers()
            self._print_storage_capacities()

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"\nSimulating {days} days from {start} "
                    f"(interval={interval}, "
                    f"seed_wheat={format_quantity('wheat', seed_wheat)})"
                )
            )

            # Fetched once - buildings themselves don't appear/disappear
            # during the simulation, only their stock does.
            granaries = list(
                Building.objects.filter(building_type="granary").select_related(
                    "population_centre"
                )
            )
            mills = list(
                Building.objects.filter(building_type="mill").select_related(
                    "population_centre"
                )
            )
            bakeries = list(
                Building.objects.filter(building_type="bakery").select_related(
                    "population_centre"
                )
            )

            # Grouped by population centre rather than one column per
            # building - a column-per-building table gets unreadably wide
            # once a world has more than a couple of villages, and the
            # per-village total is what's actually useful for tuning.
            centre_names: dict[int | None, str] = {}
            centre_granaries: dict[int | None, list] = {}
            centre_mills: dict[int | None, list] = {}
            centre_bakeries: dict[int | None, list] = {}
            for buildings, bucket in (
                (granaries, centre_granaries),
                (mills, centre_mills),
                (bakeries, centre_bakeries),
            ):
                for building in buildings:
                    cid = building.population_centre_id
                    centre_names[cid] = (
                        building.population_centre.name
                        if building.population_centre
                        else "(no centre)"
                    )
                    bucket.setdefault(cid, []).append(building)
            all_centre_ids = sorted(centre_names, key=lambda cid: centre_names[cid])

            first_bread_day = None
            min_bread = None
            worst_hunger = 0.0
            any_unfed = False

            # advance_bread_consumption_tick logs a warning per unfed
            # character - useful for the real Celery task, but pure noise
            # here since the simulation already prints an "unfed today"
            # line every interval. Quieted for the loop only, restored
            # after, so a real error elsewhere in the app during this
            # process wouldn't be silently swallowed too.
            economy_logger = logging.getLogger("general")
            previous_log_level = economy_logger.level
            economy_logger.setLevel(logging.ERROR)
            try:
                for day_offset in range(days):
                    today = start + timedelta(days=day_offset)
                    now = timezone.make_aware(datetime.combine(today, time(hour=18)))
                    should_print = day_offset % interval == 0 or day_offset == days - 1

                    advance_field_economy_tick(today=today, now=now)

                    # Snapshot each mill/bakery's own output stock either
                    # side of its tick, per building - the tick functions
                    # process every building of that type in one call, so
                    # this is the only way to attribute "produced today" to
                    # a specific building rather than a village-wide total.
                    flour_before = self._quantities_by_building(
                        GoodsStock.GoodType.FLOUR, [m.id for m in mills]
                    )
                    advance_mill_economy_tick(today=today)
                    flour_after = self._quantities_by_building(
                        GoodsStock.GoodType.FLOUR, [m.id for m in mills]
                    )

                    bread_before = self._quantities_by_building(
                        GoodsStock.GoodType.BREAD, [b.id for b in bakeries]
                    )
                    advance_bakery_economy_tick(today=today)
                    # "Produced" is read right after baking, before it's
                    # eaten - the bakery only ever bakes up to that day's
                    # demand (see advance_bakery_economy_tick), so a post-
                    # consumption reading would show 0 on every day baking
                    # keeps up, masking whether production is happening at
                    # all.
                    bread_after_baking = self._quantities_by_building(
                        GoodsStock.GoodType.BREAD, [b.id for b in bakeries]
                    )
                    bread_produced_today = sum(
                        bread_after_baking.get(b.id, 0.0) - bread_before.get(b.id, 0.0)
                        for b in bakeries
                    )

                    hunger_before = dict(
                        CharacterNeeds.objects.values_list("id", "hunger")
                    )
                    advance_bread_consumption_tick(today=today)
                    unfed_today = sum(
                        1
                        for needs_id, hunger_after in CharacterNeeds.objects.values_list(
                            "id", "hunger"
                        )
                        if hunger_after > hunger_before.get(needs_id, 0.0)
                    )

                    if unfed_today > 0:
                        any_unfed = True

                    if bread_produced_today > 0 and first_bread_day is None:
                        first_bread_day = day_offset
                    if min_bread is None or bread_produced_today < min_bread:
                        min_bread = bread_produced_today

                    hunger_values = list(
                        CharacterNeeds.objects.values_list("hunger", flat=True)
                    )
                    max_hunger = max(hunger_values) if hunger_values else 0.0
                    worst_hunger = max(worst_hunger, max_hunger)

                    if should_print:
                        # Bakery stock as of right now (post-consumption) -
                        # the bread_after_baking snapshot above is pre-
                        # consumption and only used for "made today".
                        wheat_now = self._quantities_by_building(
                            GoodsStock.GoodType.WHEAT, [g.id for g in granaries]
                        )
                        bread_now = self._quantities_by_building(
                            GoodsStock.GoodType.BREAD, [b.id for b in bakeries]
                        )

                        self.stdout.write(f"\nDay {day_offset} ({today.isoformat()})")
                        for cid in all_centre_ids:
                            parts = []
                            g_list = centre_granaries.get(cid, [])
                            if g_list:
                                wheat_qty = sum(
                                    wheat_now.get(g.id, 0.0) for g in g_list
                                )
                                parts.append(
                                    f"wheat {format_quantity('wheat', wheat_qty)}"
                                )
                            m_list = centre_mills.get(cid, [])
                            if m_list:
                                made = sum(
                                    flour_after.get(m.id, 0.0)
                                    - flour_before.get(m.id, 0.0)
                                    for m in m_list
                                )
                                stock = sum(flour_after.get(m.id, 0.0) for m in m_list)
                                parts.append(
                                    f"flour +{format_quantity('flour', made)}/"
                                    f"{format_quantity('flour', stock)}"
                                )
                            b_list = centre_bakeries.get(cid, [])
                            if b_list:
                                made = sum(
                                    bread_after_baking.get(b.id, 0.0)
                                    - bread_before.get(b.id, 0.0)
                                    for b in b_list
                                )
                                stock = sum(bread_now.get(b.id, 0.0) for b in b_list)
                                parts.append(
                                    f"bread +{format_quantity('bread', made)}/"
                                    f"{format_quantity('bread', stock)}"
                                )
                            self.stdout.write(
                                f"  {centre_names[cid]}: " + ", ".join(parts)
                            )
                        self.stdout.write(f"  unfed today: {unfed_today}")
            finally:
                economy_logger.setLevel(previous_log_level)

            self._print_verdict(first_bread_day, min_bread, worst_hunger, any_unfed)

            if not options["commit"]:
                transaction.set_rollback(True)
                self.stdout.write(
                    self.style.WARNING("\nRolled back - nothing persisted.")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("\nCommitted - simulated state persisted.")
                )

    def _seed_wheat(self, amount):
        granaries = Building.objects.filter(building_type="granary")
        for granary in granaries:
            stock, _ = GoodsStock.objects.get_or_create(
                building=granary, good_type=GoodsStock.GoodType.WHEAT
            )
            stock.quantity = min(stock.capacity, stock.quantity + amount)
            stock.save(update_fields=["quantity"])
        self.stdout.write(
            f"Seeded {format_quantity('wheat', amount)} wheat into "
            f"{granaries.count()} granary(ies)"
        )

    def _place_assigned_workers(self):
        """
        Teleport every character with a primary WORK CharacterLocation to that
        building's entrance node. The real game gets characters to work via
        the commute_tick/move_characters_tick pipeline (real-time, step-by-step
        walking), which this day-granularity forecast doesn't run - without
        this, `assign_workers` alone leaves everyone at home and labor-gated
        ticks (harvest/mill/bakery) always see zero workers present. Always
        applied, since a forecast that can never show working ticks isn't
        useful - it assumes commuting always succeeds.
        """
        work_locations = CharacterLocation.objects.filter(
            role=CharacterLocation.Role.WORK, is_primary=True
        ).select_related("character", "location")

        placed = 0
        skipped = 0
        for work in work_locations:
            entrance_node = Node.objects.filter(
                building=work.location, kind=Node.Kind.BUILDING_ENTRANCE
            ).first()
            if entrance_node is None:
                skipped += 1
                continue

            character = work.character
            character.current_node = entrance_node
            character.target_node = None
            character.is_moving = False
            character.save(update_fields=["current_node", "target_node", "is_moving"])
            placed += 1

        self.stdout.write(
            f"Placed {placed} worker(s) at their assigned building"
            + (f", skipped {skipped} (no entrance node)" if skipped else "")
        )

    def _print_storage_capacities(self):
        """
        Storage capacity is derived per-building from its InteriorSpace area
        (see GoodsStock.capacity), not a flat constant - random building
        footprints mean it varies building to building, so it's worth
        surfacing here rather than only discoverable via the shell. Summed
        per population centre (across every granary/mill/bakery it has,
        rather than one line per building) so this stays readable as a
        village gains multiple buildings of the same role.
        """
        buildings = Building.objects.filter(
            building_type__in=BUILDING_STORAGE_GOODS
        ).select_related("population_centre")
        if not buildings:
            return

        centre_names: dict[int | None, str] = {}
        totals_by_centre: dict[int | None, dict[str, list[float]]] = {}
        for building in buildings:
            centre_id = building.population_centre_id
            centre_names[centre_id] = (
                building.population_centre.name
                if building.population_centre
                else "(no centre)"
            )
            totals = totals_by_centre.setdefault(centre_id, {})
            for good_type in BUILDING_STORAGE_GOODS[building.building_type]:
                stock, _ = GoodsStock.objects.get_or_create(
                    building=building, good_type=good_type
                )
                quantity, capacity = totals.get(good_type, [0.0, 0.0])
                totals[good_type] = [
                    quantity + stock.quantity,
                    capacity + stock.capacity,
                ]

        self.stdout.write(self.style.MIGRATE_HEADING("\nGoods stored"))
        for centre_id in sorted(totals_by_centre, key=lambda cid: centre_names[cid]):
            parts = []
            for good_type in (
                GoodsStock.GoodType.WHEAT,
                GoodsStock.GoodType.FLOUR,
                GoodsStock.GoodType.BREAD,
            ):
                if good_type not in totals_by_centre[centre_id]:
                    continue
                quantity, capacity = totals_by_centre[centre_id][good_type]
                fill_percent = (quantity / capacity * 100) if capacity else 0.0
                parts.append(
                    f"{good_type} {format_quantity(good_type, quantity)}/"
                    f"{format_quantity(good_type, capacity)} ({fill_percent:.0f}%)"
                )
            self.stdout.write(f"  {centre_names[centre_id]}: " + ", ".join(parts))

    def _quantities_by_building(self, good_type, building_ids):
        if not building_ids:
            return {}
        rows = GoodsStock.objects.filter(
            good_type=good_type, building_id__in=building_ids
        ).values_list("building_id", "quantity")
        return dict(rows)

    def _print_verdict(self, first_bread_day, min_bread, worst_hunger, any_unfed):
        self.stdout.write(self.style.MIGRATE_HEADING("\nVerdict"))
        if first_bread_day is None:
            self.stdout.write("  Bread never became available in this window.")
        else:
            self.stdout.write(
                f"  First bread produced on simulated day {first_bread_day}."
            )
        if min_bread is None:
            self.stdout.write(
                "  Minimum bread baked in a single day: n/a (no days simulated)"
            )
        else:
            self.stdout.write(
                f"  Minimum bread baked in a single day: {format_quantity('bread', min_bread)}"
            )
        # worst_hunger is the peak hunger value observed, which can include
        # hunger a character already had entering the simulation (e.g. from
        # the real Celery beat schedule ticking this same economy in the
        # background - see progress_rpg/celery.py) being paid down during
        # the window, not necessarily hunger caused by it. any_unfed (did
        # any character actually miss a meal on any simulated day) is the
        # correct signal for whether *this* simulation run caused a
        # shortfall.
        self.stdout.write(
            f"  Worst hunger value reached by any character: {worst_hunger:.1f}"
        )
        if any_unfed:
            self.stdout.write(
                self.style.WARNING(
                    "  Some characters went unfed at least once - consider a larger "
                    "seed stock or more workers at granary/mill/bakery."
                )
            )

    def _print_analytic_estimate(self):
        # `boundary.area` is a GEOS geometry property computed in Python, not
        # a DB column, so it can't be summed in the ORM - same reason
        # `_maybe_ripen` reads it off the fetched subzone rather than
        # querying for it.
        total_field_area = sum(
            crop.subzone.boundary.area
            for crop in FieldCrop.objects.select_related("subzone")
            if crop.subzone.boundary is not None
        )
        population = CharacterLocation.objects.filter(
            role=CharacterLocation.Role.HOME, is_primary=True
        ).count()

        annual_bread_potential = (
            total_field_area * YIELD_PER_AREA * WHEAT_TO_BREAD_RATIO
        )
        annual_demand = population * BREAD_PER_CHARACTER_DAILY_CONSUMPTION * 365
        ramp_days = GROWTH_DURATION.days
        # Wheat-equivalent buffer to bridge from world-start to first harvest,
        # assuming best-case (uncapped) milling/baking throughput - a lower
        # bound, not a guarantee; the simulation below tests the real number.
        bridge_wheat = (
            (population * BREAD_PER_CHARACTER_DAILY_CONSUMPTION * ramp_days)
            / WHEAT_TO_BREAD_RATIO
            if WHEAT_TO_BREAD_RATIO
            else 0.0
        )

        self.stdout.write(self.style.MIGRATE_HEADING("Quick analytic estimate"))
        self.stdout.write(
            "  These figures are aggregated across all villages in the current world."
        )
        self.stdout.write(
            f"  Total registered field area across all villages: {total_field_area:.1f} m^2"
        )
        self.stdout.write(f"  Population with a home across all villages: {population}")
        self.stdout.write(
            f"  Theoretical annual bread yield across all villages "
            f"(full chain, no labor cap): {format_quantity('bread', annual_bread_potential)}"
        )
        self.stdout.write(
            f"  Annual bread demand across all villages: "
            f"{format_quantity('bread', annual_demand)}"
        )
        verdict = "surplus" if annual_bread_potential >= annual_demand else "DEFICIT"
        self.stdout.write(f"  -> {verdict}")
        self.stdout.write(
            f"  Suggested starting wheat seed per granary to bridge the {ramp_days}-day growth "
            f"window (best case, ignores labor caps): "
            f"{format_quantity('wheat', bridge_wheat)}"
        )
        self.stdout.write(
            "  This is a lower bound - real throughput is capped by workers present "
            "at the mill/bakery in each village. Use --seed-wheat with the simulation below to check "
            "whether a given amount actually survives the ramp-up.\n"
        )
