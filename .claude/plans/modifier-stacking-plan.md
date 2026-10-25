# XP modifier stacking — mixed additive/multiplicative composition

Enables authoring more modifiers, with each one declaring whether it stacks
additively or multiplicatively.

Supersedes the "document the stacking rule" item that was originally item 3 of
`.claude/plans/readability-audit-top-five-plan.md`. That item assumed the
current single-product rule was staying; it isn't, so a comment describing it
would be obsolete on arrival.

Background on the current behaviour: `docs/design-notes/codebase-re-entry-audit.md` §3, §5.

---

## 1. High-level strategy

Today `progression/ap.py:73-81` multiplies every active `XpModifier` together.
That cannot express "some additive, some multiplicative", so the composition
rule itself has to change.

The rule to adopt:

```
total = (1 + Σ(additive_i − 1)) × Π(multiplicative_j)
```

Additive modifiers sum within their bucket; the bucket then multiplies with the
multiplicative ones. The property worth having is that **order does not
matter** — addition commutes within the bucket, multiplication commutes across
buckets — so there is no precedence to define, document, or forget. That is the
main reason to prefer this shape over any sequenced pipeline.

Sequenced so that every step before the behaviour change is a provable no-op:
remove a write nothing reads, add a field defaulting to today's behaviour, then
change the rule. Each step is independently revertable, and only step 3 can
move a single number in production.

Scope note: this plan covers character scope, which is the only scope with a
live read path. Player scope is prepared for but not wired up — see §4.

---

## 2. Files likely to change

All exist; no new source files.

- `gameplay/services/xp_modifiers.py` — drop the player-scope `activity_active`
  write; add the key→stacking-mode mapping.
- `gameplay/models.py` — `XpModifier.stacking` field; `Meta.constraints`.
- `gameplay/migrations/` — **new**, two auto-generated (`AddField`, then
  `AddConstraint`). Kept in separate commits so the constraint can be reverted
  without losing the field.
- `progression/ap.py` — the two-bucket composition in `get_multiplier`.
- `progression/models.py:869-907` — expose bucket subtotals in the character
  reward breakdown.
- `gameplay/tests/test_xp_modifiers.py` — player-scope assertions.
- `progression/tests/test_ap.py` — composition tests.

---

## 3. Implementation plan

### Commit 1 — remove player-scope `activity_active`
Delete `ACTIVITY_ACTIVE_PLAYER_MULTIPLIER` and the player-scope branch of
`set_activity_active_modifiers`, collapsing its two-scope loop to a single
character lookup.

Behaviourally a no-op in production: nothing reads player-scope modifiers
(`progression/models.py:885` is the only consumer of `get_xp_multiplier()` and
it reads `self.character`). The modifier was also tautological — it was active
exactly when the player was recording, and recorded activity is the only source
of player AP, so it would have multiplied every unit of AP it could ever apply
to. That is a base-rate change, not a modifier.

`XpModifier.Scope.PLAYER` **stays on the model** — it is the right home for the
genuinely player-level modifiers this plan enables (events, streaks, seasonal).
It simply has no occupant until one is authored.

Do this first: it removes a scope from the function that commits 2–3 extend,
so the extension is written against the simpler shape.

### Commit 2 — add the `stacking` field
`XpModifier.stacking`, a `TextChoices` (`ADDITIVE` / `MULTIPLICATIVE`),
**defaulting to `MULTIPLICATIVE`**. Existing rows therefore keep today's
behaviour exactly and the migration is behaviourally inert.

Add a key→mode mapping in `xp_modifiers.py` beside the existing
`PLAYER_ONLINE_KEY`/`ACTIVITY_ACTIVE_KEY` constants, and have
`activate_link_modifier` set the field from it. Code-created rows are then
consistent by construction; the admin remains the escape hatch.

### Commit 3 — the composition rule
Rewrite `get_multiplier` to the two-bucket formula. **This is the only commit
that can change a number in production**, and with both current modifiers
defaulted to `MULTIPLICATIVE` it should not: `1.25 × 1.5 = 1.875` before and
after. Existing `test_ap.py` tests passing unmodified is the evidence.

> **Commits 2 and 3 must land together.** Commit 2 adds the field; commit 3 is
> what reads it. Landing 2 alone leaves a field nothing consumes — precisely
> the write-only pattern commit 1 exists to delete. Separate commits for
> reviewability, one merge.

Note that both buckets will be live before any additive modifier is authored.
That is intentional: the mechanism is inert until a key is mapped to
`ADDITIVE`, and having it ready means authoring the first additive modifier is
a one-line mapping entry rather than a schema change and a composition rewrite
in the middle of designing a feature.

### Commit 4 — unique constraint
Add a `UniqueConstraint` per scope so `(key, owner)` cannot duplicate.
`activate_link_modifier`'s `update_or_create` already assumes this; right now
it holds by convention only, and more keys means more chances to break it.
See §5 for the NULL gotcha and the pre-flight check this needs.

### Commit 5 — surface the buckets in the breakdown
`boost_multiplier` becomes a collapsed product of two buckets. Add the subtotals
as **new** keys in `CharacterActivity.get_xp_reward_summary` so the breakdown
stays legible. Additive only — never rename or remove a key; see §5.

---

## 4. Design decisions

### Two buckets vs an ordered pipeline vs all-additive
**Chosen:** additive bucket, then multiply. Order-independent, which is what
keeps it re-enterable.
**Alternative A — ordered pipeline** (each modifier applies to the running
total, sequenced by a priority field). Rejected: it makes the result depend on
an ordering that must be authored and maintained, and reintroduces exactly the
precedence question this is meant to settle.
**Alternative B — all additive.** Rejected: the user wants both, and
multiplicative is the right shape for a boost that should scale with everything
else rather than be diluted by a growing additive pool.

### "Additive" means additive *percentage*, not flat addition
**Decided.** An additive modifier contributes a percentage that sums with other
additive percentages: `+25%` and `+25%` give `+50%`, and that bucket then
multiplies with the multiplicative ones.

**Alternative — flat addition** (`+10 AP` added to the base irrespective of
multipliers). Rejected, and worth recording *why the question arose*: a flat
bonus is not a multiplier at all. It could not live in `get_multiplier`'s
return value, which is a single `Decimal` factor; it would need a separate term
in the reward formula plus a decision about where it applies relative to the
multipliers. Anyone reading "additive" later should not have to re-open that
question — it is settled as percentage.

### The number means "+X%" in both modes
**Chosen:** keep the single `multiplier` field. `1.25` always reads as "+25%";
the mode decides whether that 25% joins the sum or the product. An additive row
contributes `multiplier − 1` to the bucket.
**Alternative:** a separate `bonus` field for additive rows. Rejected: it needs
a constraint that exactly one of the two is set, gives a reader two fields to
check, and requires a data migration. One number with one reading is the
cheaper thing to re-enter.

### Mode on the row, mapping in the service
**Chosen:** the field lives on `XpModifier`, but `xp_modifiers.py` owns the
key→mode mapping so every code-created row is consistent.
**Alternative — a `ModifierDefinition` table** keyed by `key`, owning mode,
default multiplier and display name. That is the more correct model (mode is a
property of the modifier *type*, not the instance) and is where this ends up if
the set grows large or becomes admin-authored. Rejected **for now**: it is a
new model, a new migration and a new admin for two existing keys. Revisit when
the set reaches roughly half a dozen keys or when non-engineers need to author
them.

### `MULTIPLICATIVE` as the field default
**Chosen:** preserves current behaviour on migration with no data migration and
no test churn.
**Alternative — default `ADDITIVE`**, on the theory that most future modifiers
will be additive. Rejected: it would silently change the live boost from 1.875
to 1.75 as a side effect of a schema migration. If additive becomes the common
case, change the field default later — that affects new rows only.

### No cap
Deliberately excluded. A cap is a balance decision, it is trivial to add later
in one place, and the additive bucket already bounds the growth that motivated
the original concern. `xp_mastery_multiplier_cap` is the precedent to follow if
one is wanted — a `GameSettings` value, not a hardcoded constant.

---

## 5. Edge cases

**Migration / data integrity**
- Commit 4's constraint will **fail on existing duplicate rows**. Check for
  duplicates on `(scope, key, owner)` in each environment before deploying, and
  clean up if found. Do not add a blind data migration that deletes rows — a
  duplicate is a symptom worth looking at.
- **Postgres treats NULLs as distinct in unique constraints.** `player` and
  `character` are both nullable, so a single
  `UniqueConstraint(fields=["scope", "key", "character"])` will not prevent
  duplicate player-scope rows. Two conditional constraints are needed, one per
  scope, each guarded on the relevant FK being non-null.
- Commit 2's `AddField` on a table with existing rows: confirm the default is
  applied rather than leaving nulls.

**Composition**
- Empty bucket must yield the identity (1), not 0 — an all-multiplicative set
  must produce exactly today's answer.
- `multiplier` is `DecimalField(max_digits=6, decimal_places=3)`. Keep the
  arithmetic in `Decimal` throughout; do not round intermediate bucket
  subtotals.
- **Penalties are not expected.** No modifier below 1.0 is planned, so the
  additive bucket cannot be driven to zero or negative in normal use. Enforce
  this by **validating `multiplier >= 1` on the admin form** rather than
  clamping inside `get_multiplier` — fail at the point of entry and keep the
  composition function arithmetic-only. If penalties are ever wanted, the floor
  decision comes back with them.

**Backwards compatibility**
- `reward_breakdown` is a persisted `JSONField` (`progression/models.py:421`),
  exposed via `progression/serializers.py:87,307` and read by the frontend at
  `useActivityTimer.ts:373-375`, `useActivityInput.ts:62-65`. Historical rows
  are snapshots and are never backfilled. Commit 5 may only **add** keys.
- `get_multiplier` also drives `get_productivity` (`progression/ap.py:103`), so
  the character productivity signal moves with this. Expected, but it is a
  second consumer to check.

**Concurrency**
- The new constraint makes `activate_link_modifier` genuinely race-safe:
  concurrent callers currently rely on convention, and the loser of a race will
  now hit an `IntegrityError` that `update_or_create` handles by re-fetching.
  This is a reason to add the constraint, not merely hygiene.
- No new locking is needed. The modifier writes are already inside
  `@transaction.atomic`.

---

## 6. Tests

**New — `progression/tests/test_ap.py`:**
Until the first additive modifier is authored, these tests are the **only**
exercise of the additive path — no production code will hit it. That makes them
load-bearing rather than incidental: they are what stops the bucket rotting
before it has an occupant.

- Additive bucket only: two `+25%` additive modifiers give 1.5, not 1.5625.
- Multiplicative bucket only: unchanged from today.
- Mixed: additive bucket multiplies with the multiplicative one.
- Bucket identity: all-multiplicative set produces exactly the pre-change value.
- Order independence: creating the same set of rows in a different order gives
  the same result.

**Existing — modify:**
- `test_ap.py:92` `test_multiple_active_modifiers_multiply` — should keep
  passing untouched (rows default to `MULTIPLICATIVE`). If it needs editing,
  the default is wrong. Make the mode explicit afterwards so intent is visible.
- `test_ap.py:132` `test_works_for_player_scope_too` — **survives commit 1**; it
  uses a generic `player_test_modifier` key, not `activity_active`. Keep it: it
  is what pins player scope as still-supported.
- `test_xp_modifiers.py:154` `test_activating_creates_character_and_player_modifiers`
  — rename, drop the player assertions, expect one modifier not two.
- `test_xp_modifiers.py:182` and `:208` — drop `player_mod`; in `:208` the
  revoke count becomes 1 and the final row count becomes 1.
- `test_xp_modifiers.py:38` `test_can_target_player_scope` — keep unchanged; it
  tests `activate_link_modifier`'s generic capability, not `activity_active`.

Run scoped test units only (`gameplay`, `progression`); full suites are the
user's to run.

---

## 7. Risks

- **Defaulting the field to `ADDITIVE`** — silently rebalances every existing
  boost via a schema migration. The single most damaging mistake available here.
- **Adding the constraint without checking for duplicates first** — a failed
  migration mid-deploy.
- **Writing one constraint instead of two** and assuming NULLs collide. It will
  pass tests against character-scope data and silently permit duplicate
  player-scope rows later.
- **Renaming `boost_multiplier`** while making the breakdown legible. Breaks
  historical snapshots and the frontend reads.
- **Folding commits 1–2 into commit 3** — losing the property that only one
  commit can change a number, which is what makes this safely revertable.
- **Treating the additive bucket as `Σ multiplier`** rather than
  `1 + Σ(multiplier − 1)`. Two `1.25` additive modifiers would give 2.5 instead
  of 1.5.

---

## 8. Open questions

1. **Which future modifiers are additive?** None exist yet, and none is needed
   to land this — `player_online` and `activity_active` both stay
   multiplicative, so the mapping ships with an empty additive set and the
   bucket is simply inert. The open part is only which of the planned
   events/streaks/seasonal modifiers should be additive when they are authored.
   The *semantics* are settled (additive percentage — see §4).
2. **Should `xp_mods` in the bootstrap payload be populated?** It is a declared
   API field (`api/serializers.py:149`) read by the frontend
   (`useBootstrapGameData.ts:60`) but hardcoded to `[]` at `api/views.py:773`.
   Out of scope here, but this plan is what would make it worth filling — and
   character links are not yet player-visible, which may be the reason it is
   empty.
