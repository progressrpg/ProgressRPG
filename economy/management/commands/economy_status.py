from django.core.management.base import BaseCommand

from economy.constants import format_quantity, format_rate
from economy.services.capacity_services import population_capacity_report
from locations.models import Building, PopulationCentre

# (report attribute, display label, good_type, unit_label) for each
# production role in a capacity report, in the order they're printed -
# good_type picks the unit (format_rate) and unit_label names what
# building_count is counting, since that differs per role (bakeries/mills
# are buildings, but "fields" counts FieldCrop plots, not the
# field_shelter buildings behind them).
CAPACITY_LINES = [
    ("farming", "Farming", "wheat", "field(s)"),
    ("milling", "Milling", "flour", "mill(s)"),
    ("baking", "Baking", "bread", "bakery(ies)"),
]


class Command(BaseCommand):
    help = (
        "Print a snapshot of current economy state per population centre: "
        "goods stocks and conversion status per building, plus whether "
        "current population/infrastructure/workers give it enough daily "
        "production capacity to sustain itself."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--centre",
            help="Only show this population centre (by name)",
        )

    def handle(self, *args, **options):
        centres = PopulationCentre.objects.all().order_by("name")
        if options["centre"]:
            centres = centres.filter(name=options["centre"])
            if not centres.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"No PopulationCentre named {options['centre']!r}"
                    )
                )
                return

        if not centres.exists():
            self.stdout.write("No population centres found.")
            return

        buildings_by_centre: dict[int | None, list[Building]] = {}
        buildings = (
            Building.objects.filter(population_centre__in=centres)
            .prefetch_related("goods_stocks", "conversion_states")
            .order_by("building_type", "name")
        )
        for building in buildings:
            buildings_by_centre.setdefault(building.population_centre_id, []).append(
                building
            )

        for centre in centres:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n{centre.name}"))

            for building in buildings_by_centre.get(centre.id, []):
                self._print_building(building)
            if centre.id not in buildings_by_centre:
                self.stdout.write("  No buildings.")

            self._print_population_capacity(centre)

    def _print_building(self, building):
        self.stdout.write(f"  {building.name} [{building.building_type}]")

        stocks = list(building.goods_stocks.all())
        if stocks:
            for stock in stocks:
                quantity = format_quantity(stock.good_type, stock.quantity)
                capacity = format_quantity(stock.good_type, stock.capacity)
                self.stdout.write(f"    {stock.good_type}: {quantity} / {capacity}")
        else:
            self.stdout.write("    (no goods stored)")

        for state in building.conversion_states.all():
            self.stdout.write(
                f"    {state.activity} last processed: {state.last_processed_on}"
            )

    def _print_population_capacity(self, centre):
        """
        Population needs vs. production capacity: whether this centre's
        current infrastructure and present workers can feed its resident
        count, per economy.services.capacity_services.
        population_capacity_report. Printed for every population centre,
        even ones with no buildings at all - a centre with residents and
        zero bakeries is exactly the shortfall this section exists to
        surface.
        """
        report = population_capacity_report(centre)

        self.stdout.write("\n  Population:")
        self.stdout.write(f"    {report.resident_count} resident(s)")

        self.stdout.write("\n  Daily demand:")
        self.stdout.write(
            f"    Bread: {format_rate('bread', report.daily_bread_demand)}/day"
        )
        self.stdout.write(
            f"    Flour: {format_rate('flour', report.daily_flour_demand)}/day"
        )
        self.stdout.write(
            f"    Wheat: {format_rate('wheat', report.daily_wheat_demand)}/day"
        )

        self.stdout.write("\n  Production capacity:")
        for attr, label, good_type, unit_label in CAPACITY_LINES:
            self._print_capacity_line(
                label, unit_label, good_type, getattr(report, attr)
            )

    def _print_capacity_line(self, label, unit_label, good_type, line):
        self.stdout.write(f"    {label}:")
        self.stdout.write(
            f"      {line.building_count} {unit_label}, "
            f"{line.workers_present} worker(s) present"
        )
        self.stdout.write(
            f"      Capacity: {format_rate(good_type, line.capacity_per_day)}/day"
        )

        surplus = format_rate(good_type, line.surplus_per_day, signed=True)
        if line.is_shortfall:
            status = self.style.WARNING(f"SHORTFALL ({surplus}/day)")
        else:
            status = self.style.SUCCESS(f"OK (surplus {surplus}/day)")
        self.stdout.write(f"      Status: {status}")
