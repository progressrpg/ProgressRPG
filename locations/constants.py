# Web Mercator (EPSG:3857) - the project's working CRS for every in-game
# coordinate: Node/Building/Character locations, Path geometries, movement
# math. Named here rather than left as a bare srid=3857 kwarg scattered
# across models/services/management commands, so there's one place that
# says what the number is.
PROJECT_SRID = 3857
