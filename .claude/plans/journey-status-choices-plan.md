# Journey.status — TextChoices and the "cancelled" bug

Resolves the data-integrity question from
`docs/design-notes/codebase-re-entry-audit.md` §4 (blocks):
`locations/models.py:296`'s `Journey.status` has no `choices`, and
`locations/management/commands/place_characters.py:112` writes
`status="cancelled"`, a value nothing else in the codebase recognises.

**Decision (confirmed with you):** `"cancelled"` is a bug, not an intentional
third state. Re-placing a mid-journey character should end that journey the
same way `Journey.cancel()` already does — `status="complete"` — not invent a
new value. Nothing today reads a distinction between "arrived" and
"interrupted", so there is nothing to lose by unifying them.

Background: `docs/design-notes/codebase-re-entry-audit.md` §4; audit §1's
`working-memory-load-plan.md` §8 flags this same finding and defers it here.

---

## 1. High-level strategy

Two independent changes, sequenced so the bug fix doesn't have to wait on
the broader cleanup and vice versa:

1. Fix `place_characters.py:112` to end a journey the same way
   `Journey.cancel()` does, instead of writing an unrecognised value.
2. Give `Journey.status` real `choices` (`Journey.Status(TextChoices)`,
   mirroring `Timer.Status`/`Node.Kind`/`ActivityDefinition.Kind` — the
   repo's established pattern) and sweep the ~10 hardcoded `"active"`/
   `"complete"` literal sites onto it, so the state machine has one
   documented source of truth instead of string literals scattered across
   `movement.py`, `views.py`, `tasks.py`, `serializers.py`, and tests.

The bug fix (commit 1) is the one with actual behavioural consequence and
could ship alone. The `TextChoices` sweep (commit 2) is pure readability —
same shape as the `Timer.STATUS_CHOICES` → `TextChoices` conversion already
done in #829 — and is safe to do in the same PR since it's the literal
audit finding this plan exists to close.

---

## 2. Files likely to change

All existing files; no new files except a migration.

| File | Why |
|---|---|
| `locations/models.py` | Add `Journey.Status(TextChoices)`; add `choices=`/typed default to the `status` field; sweep internal literal comparisons (`is_complete`, `advance_node`, `cancel`, `Movable.current_journey`, the `uniq_active_journey_per_character` constraint's `condition=`). |
| `locations/management/commands/place_characters.py` | The bug fix — stop writing `"cancelled"`. |
| `locations/services/movement.py` | Sweep 3 literal sites (`:133`, `:158`, `:217`). |
| `locations/tasks.py` | Sweep 1 literal site (`:63`). |
| `locations/views.py` | Sweep 4 literal sites (`:105`, `:258`, `:314`, `:359`). |
| `locations/serializers.py` | Sweep 1 literal site (`:125`). |
| `locations/migrations/00XX_journey_status_choices.py` (new) | Hand-written `AlterField` adding `choices=` — metadata-only, no DB column change (still `CharField(max_length=20)`), but Django tracks `choices` in migration state so an unmade migration would show up in `makemigrations --check`. |
| `locations/tests/test_models.py`, `locations/tests/test_character_serializers.py`, `locations/tests/test_population_centre_views.py` | Existing tests construct `Journey`s with `status="active"` string literals — leave those as-is (a literal that matches a `TextChoices` value is still valid input, Django doesn't require call sites to use the enum), but add one new test for the bug fix. |

---

## 3. Implementation plan

### Commit 1 — fix `place_characters.py`: reuse `Journey.cancel()`

- Replace the queryset `.update(status="cancelled")` with a per-instance
  call to the existing `Journey.cancel()` method — the character has at
  most one active journey (enforced by `uniq_active_journey_per_character`),
  so this is fetching one row, not a bulk operation:
  ```python
  active_journey = char.journeys.filter(status=Journey.Status.ACTIVE).first()
  if active_journey:
      active_journey.cancel()
  ```
  replacing the `if char.is_moving: char.journeys.filter(...).update(...)`
  block. `Journey.cancel()` already sets `finished_at` (the bulk `.update()`
  didn't) and flips `character.is_moving = False` — the current code relies
  on `char.assign_home(building)` a few lines below to eventually correct
  `is_moving`/position, so double check that ordering still holds (see Edge
  cases) rather than assuming it's a pure improvement for free.
- This commit alone fixes the data-integrity gap even before commit 2 lands
  — it stops writing a value nothing recognises.

### Commit 2 — `Journey.Status(TextChoices)` and literal sweep

- Add to `Journey`, mirroring `Timer.Status`'s shape:
  ```python
  class Status(models.TextChoices):
      ACTIVE = "active", "Active"
      COMPLETE = "complete", "Complete"
  ```
- Change the field to
  `models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)`,
  replacing the `# e.g., active, complete` comment the choices now make
  redundant.
- Sweep internal `Journey`/`Movable` comparisons: `is_complete` (`status ==
  self.Status.COMPLETE`), `advance_node`'s guard and terminal assignment,
  `cancel()`'s assignment, `Movable.current_journey`'s filter, and the
  `uniq_active_journey_per_character` constraint's `condition=Q(status=...)`.
- Sweep the 9 external literal sites listed in the Files table
  (`movement.py` ×3, `views.py` ×4, `tasks.py` ×1, `serializers.py` ×1) to
  `Journey.Status.ACTIVE` / `Journey.Status.COMPLETE`.
- Hand-write the migration (no Django environment available to generate one
  — same constraint as the earlier `Timer.Status`/`XpModifier.stacking`
  migrations in #829/#833) as a single `AlterField`, following
  `locations/migrations/0009_alter_building_building_type.py`'s shape.
- No behaviour change: same two string values, same default, only named now.

---

## 4. Design decisions

- **Unify "cancelled" into "complete" rather than adding a third status.**
  Alternative (the one I raised and you declined): a real `CANCELLED` value,
  with `is_complete` (or a new `is_finished`) recognising both terminal
  states. Rejected per your call — nothing today reads the distinction, and
  a status value with no reader is exactly the kind of thing that becomes
  the *next* "why is this here" audit finding. If a future feature wants to
  distinguish "arrived" from "interrupted" (e.g. player-visible journey
  history, analytics), that's a new finding to raise then, not a state to
  carry speculatively now.
- **Reuse `Journey.cancel()` rather than changing the bulk `.update()`'s
  value in place.** Alternative: keep the queryset `.update(status=...)`
  call, just change the string to `"complete"`. Rejected — `cancel()`
  already exists, already sets `finished_at`, and is the codebase's one
  documented way to end a journey early; a second inline path that
  duplicates `status`+`finished_at` assignment is the same "two ways to do
  one thing" pattern the audit flags elsewhere (§5). Since a character has
  at most one active journey, there's no bulk-update performance reason to
  avoid the instance method.
- **Ship the `TextChoices` sweep in the same PR as the bug fix**, rather
  than as a separate follow-up. Alternative: land the one-line bug fix
  alone and defer the `choices=`/sweep to later. Rejected — the audit
  finding this plan closes *is* the missing `choices=`; fixing only the
  symptom (`"cancelled"`) and leaving the field with no `choices` would
  leave the actual audit item open. The two are small enough together to
  stay one reviewable PR.

---

## 5. Edge cases

- **`place_characters.py`'s ordering**: `Journey.cancel()` sets
  `character.is_moving = False` and saves it. The existing code immediately
  calls `char.assign_home(building)` afterward — confirm `assign_home`
  doesn't assume `is_moving` is still `True` at that point (unlikely, but
  worth a read at implementation time since this is the one place where
  reusing `cancel()` changes behaviour, not just naming).
- **No DB schema change** — `choices` is Django/Python-level validation
  only; the migration is metadata (`AlterField`), not a column alteration.
  No backfill, no data migration needed.
- **Existing rows with `status="cancelled"`** (if any exist in a live/staging
  DB from `place_characters` having already run): `choices` validation only
  applies on `full_clean()`/forms, not on read or plain `.save()`, so
  existing `"cancelled"` rows won't raise on load — but they'll keep
  reporting `is_complete=False` forever, same as today, since this plan
  doesn't backfill historical data. Worth a one-off manual check (not part
  of this plan) if you want existing rows cleaned up:
  `Journey.objects.filter(status="cancelled").update(status="complete", finished_at=F("started_at"))`
  or similar — flagged in Open Questions rather than assumed.
- **Backwards compatibility**: field default and both real values are
  unchanged (`"active"`/`"complete"`), so no serializer/API-shape change;
  `serialize_for_client()`'s `"status": self.status` still emits the same
  strings.

---

## 6. Tests

- New test for commit 1: re-placing a mid-journey character via
  `place_characters` (or calling the extracted logic directly) ends their
  active journey with `status == Journey.Status.COMPLETE` and `finished_at`
  set, not `"cancelled"`.
- Existing `locations/tests/test_models.py` (`Journey.advance_node`,
  `Journey.cancel` presumably covered already — confirm) should pass
  unmodified after commit 2; re-run scoped to confirm.
- Existing tests constructing `Journey(status="active")` by string literal
  continue to work unmodified — `choices` doesn't reject valid literals,
  only invalid ones on `full_clean()`. No forced rename of every test call
  site.
- If any test currently asserts on `"cancelled"` as a value (grep found
  none in the codebase at time of writing — only `place_characters.py`
  itself writes it), that assertion would need updating; confirm at
  implementation time.

---

## 7. Risks

- **Reordering side effects in `place_characters.py`** — swapping a bulk
  `.update()` for an instance `.cancel()` call changes *when*
  `character.is_moving`/`finished_at` get set relative to the rest of the
  function. Low risk (this is a management command, not a hot path) but
  worth the explicit ordering check called out in Edge cases rather than
  assuming it's a no-op.
- **Migration drift** — same class of risk as the earlier hand-written
  migrations in this session: no Django environment to run
  `makemigrations --check --dry-run` or `migrate` before landing. Verify
  locally before merge, same caveat as #829/#833/#835.
- **Missing a literal site during the sweep** — 9 external sites plus 5
  internal ones; a missed one wouldn't break anything at runtime (the
  string value is identical) but would leave a stray hardcoded literal the
  next audit would re-flag. Grep for `status="active"`/`status="complete"`/
  `status=\"active\"`/`.status ==` across `locations/` after the sweep to
  confirm none remain outside tests.

---

## 8. Open questions

- Should existing `"cancelled"` rows (if any exist in staging/prod from
  `place_characters` already having run there) be backfilled to
  `"complete"` as a one-off data cleanup? Not included in this plan's
  scope — flagging so it isn't silently forgotten if such rows exist.
- `place_characters_task` (`locations/tasks.py:223-224`) isn't currently on
  the Celery beat schedule (confirmed absent from `progress_rpg/celery.py`)
  but is invokable manually. Worth confirming it's not triggered from
  anywhere else (an admin action, a management UI) that this plan didn't
  search — if it is, the bug fix is more load-bearing than "management
  command edge case."
