"""
Fixed placement grid for imported watabou villages (see import_villages),
so re-running the pipeline always lays villages out the same way instead of
scattering them at random each time.

VILLAGE_LAYOUT is a flat list of (x, y) origins in metres (SRID 3857),
row-major across a square grid centred on (0, 0). Extend it by raising
GRID_COLUMNS/GRID_ROWS or SLOT_SPACING if locations/data/ grows past the
current slot count.
"""

GRID_COLUMNS = 5
GRID_ROWS = 5
# Metres between adjacent slot centres - comfortably clears a village's
# typical extent (a few hundred metres) plus the --min-distance villages
# used to be kept apart by.
SLOT_SPACING = 3000

VILLAGE_LAYOUT: list[tuple[int, int]] = [
    (
        int((col - (GRID_COLUMNS - 1) / 2) * SLOT_SPACING),
        int((row - (GRID_ROWS - 1) / 2) * SLOT_SPACING),
    )
    for row in range(GRID_ROWS)
    for col in range(GRID_COLUMNS)
]
