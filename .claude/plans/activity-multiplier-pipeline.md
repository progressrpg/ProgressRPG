# Activity reward multiplier pipeline

Analysis only — no code changes in this document's scope. Follow-on from
`.claude/plans/progression-track-abstraction.md` (Phases 1–2, PRs #711/#712),
which left AP/skill-XP formulas live-derived but multiplier composition
still ad hoc.

---

## 1. High-level strategy

Replace the hand-rolled `multiplier *= x` chains in `PlayerActivity`/
`CharacterActivity.get_xp_reward_summary` with one shared, named,
composable multiplier list, combined by a single function that supports
both multiplicative (compounding) and additive (same-bucket-stacking)
modes. `XpModifier` gets the same mode concept so owner-scoped event
bonuses (streaks, premium, future events) flow through the identical
combination rule as structural, rule-based bonuses (mastery, task,
skill-link). `reward_breakdown` gains one named entry per contributing
multiplier instead of a fixed field per multiplier, so adding a new
multiplier later never requires a schema/breakdown-shape change again.

---

## 2. Files likely to change

- `progression/points.py` (exists) — add `MultiplierMode`,
  `MultiplierComponent`, `combine_multipliers()`; extend `activity_multipliers()`-
  style helper(s) that assemble the structural component list (mastery,
  task, kind-discount, new skill-link bonus).
- `progression/ap.py` (exists) — `get_multiplier()` changes shape: return
  `list[MultiplierComponent]` (one per active `XpModifier` row, tagged with
  its stored mode) instead of one pre-multiplied `Decimal`.
- `gameplay/models.py` (exists) — `XpModifier` gets a `mode` field
  (choices, default `multiplicative`); new migration.
- `progression/models.py` (exists) — `PlayerActivity`/
  `CharacterActivity.get_xp_reward_summary` rewritten to assemble a full
  component list and call `combine_multipliers()`; `reward_breakdown`
  shape changes.
- `users/models.py` (exists) — `Person.get_xp_multiplier`,
  `Player.get_activity_xp_multiplier` — see §4 for the asymmetry that
  needs resolving here.
- Frontend reward-breakdown renderer (the util extracted in #698 for
  `ActivityRewardScreen`) — needs updating for the new list-shaped
  breakdown; exact file to confirm during implementation.
- `core/tests.py` — asserts `player.get_activity_xp_multiplier()`'s return
  value directly (lines ~195–211); needs updating if that signature changes.

---

## 3. Implementation plan

1. Add `MultiplierMode`/`MultiplierComponent`/`combine_multipliers()` to
   `progression/points.py`, with unit tests only — pure new code, no
   call sites touched, no behavior change.
2. Add `XpModifier.mode` (migration, default `multiplicative` — existing
   rows unaffected, no backfill needed).
3. Change `ap.get_multiplier()` to return `list[MultiplierComponent]` built
   from a person's active `XpModifier` rows. Resolve the `Person`/`Player`
   asymmetry (§4) as part of this step, not silently.
4. Rewrite `PlayerActivity`/`CharacterActivity.get_xp_reward_summary` to
   build the full component list (structural + `XpModifier`-derived) and
   call `combine_multipliers()`; update `reward_breakdown` shape.
5. Add the skill-link bonus as the first genuinely new component + a
   `GameSettings` tunable — proves the pipeline end-to-end with a real
   addition.
6. Update the frontend reward-breakdown renderer for the new shape.

Each step is a small, independently reviewable PR, stacked in order —
matching how Phases 1/2 were split.

---

## 4. Design decisions

**Component list with explicit mode, not inferred from position/type.**
Alternative: infer mode by convention (e.g. "kind multipliers are always
multiplicative"). Explicit is preferable — no hidden assumptions, and a
reviewer can see the stacking rule for a new multiplier at the call site
where it's added.

**Uniform factor semantics regardless of mode** (`1.25` always means
"+25%", whether it joins the additive bucket or multiplies independently).
Alternative: store additive components as a raw bonus delta (`0.25`)
instead of a factor. Uniform factors are simpler to read in the breakdown
and avoid a second numeric convention.

**One `combine_multipliers()` used for both structural multipliers and
`XpModifier` rows**, rather than keeping `XpModifier`'s aggregation
separate (status quo). Avoids reimplementing the additive/multiplicative
math a second time when a third multiplier source appears later.

**Resolve the Player/Character asymmetry, don't paper over it.**
Currently `Character.get_xp_multiplier()` (inherited from `Person`) reads
`XpModifier`; `Player.get_activity_xp_multiplier()` is unrelated — it's
purely the premium-subscription flag (`1.0` or
`GameSettings.premium_activity_xp_multiplier`) and never touches
`XpModifier` at all. Player-scoped `XpModifier` rows (`Scope.PLAYER`) exist
in the model but are only ever created in commented-out code
(`gameplay/services/xp_modifiers.py`) — dead for reward purposes today.
Two options:
  - (a) Wire `PlayerActivity.get_xp_reward_summary` to also pull
    `ap.get_multiplier(player)` components alongside the premium flag,
    activating Player-scoped `XpModifier`s as part of this change.
  - (b) Leave Player-side `XpModifier` consumption out of scope — migrate
    Character's existing usage into the pipeline, keep the premium flag as
    its own structural component for Player, and treat "activate Player
    `XpModifier`s" as a separate, deliberate follow-up.
  Recommend (b): activating a previously-dead code path is a behavior
  change beyond "compose existing multipliers better," and deserves its
  own review/decision rather than riding along here. Flagged as an open
  question below in case the answer is actually "yes, do it now."

**Default every existing multiplier to `multiplicative` on introduction.**
Matches current behavior exactly (singleton buckets make the two modes
identical), defers "which multipliers should stack additively" to a
balance decision made when a second multiplier actually lands in the same
bucket — not decided speculatively here.

---

## 5. Edge cases

- Empty/singleton component lists must resolve to identity (`1.0`) or the
  single factor unchanged — should fall out of `combine_multipliers()`'s
  construction, call out in tests explicitly.
- A large negative additive stack could in principle drive the combined
  additive factor at or below zero — clamp the additive bucket's combined
  factor to a floor (e.g. `>= 0`) so AP/XP can't go negative.
- `XpModifier` rows read live during `get_xp_reward_summary()` (a row's
  `is_active`/`ends_at` could change concurrently) — pre-existing behavior,
  not a new risk introduced by this change.
- `reward_breakdown` is a write-once snapshot on already-completed
  activities; historical rows keep the old fixed-key shape forever. The
  frontend renderer needs to handle both old and new shapes — consider a
  shape/version marker in `reward_breakdown` so it doesn't have to guess
  from key presence (see open questions).
- Migration is additive-only (new nullable/defaulted field), no backfill
  required.

---

## 6. Tests

- `combine_multipliers()`: empty list, single multiplicative, single
  additive (both degenerate to the same value), multiple multiplicative
  (compounds), multiple additive (sums then applies once), mixed bucket.
- `XpModifier.mode`: default on new/existing rows; `get_multiplier()`'s
  component output tags each row's mode correctly.
- `PlayerActivity`/`CharacterActivity.get_xp_reward_summary`: extend
  `test_premium_activity_rewards.py` (and the Character equivalent) to
  assert identical `xp_gained` for existing single-multiplier scenarios
  (behavior preservation), plus a new case with 2+ additive multipliers
  active to prove the stacking math.
- Skill-link multiplier (step 5): mirror
  `test_prior_skill_xp_boosts_mastery_multiplier`'s pattern — bonus applies
  only when the activity/`ActivityDefinition` has a skill set.

---

## 7. Risks

- Changing `get_multiplier()`'s return shape without checking every caller
  could silently break a Decimal-expecting call site — `core/tests.py`
  already asserts `get_activity_xp_multiplier()`'s return value directly;
  grep for all callers before touching either signature.
- Silently reclassifying an existing multiplier's mode while wiring it into
  the pipeline would change live reward balance without a balance
  decision — mitigate by keeping every existing multiplier
  `multiplicative` and diffing old-vs-new `xp_gained` for identical inputs
  in tests.
- Inconsistent understanding of "additive" between future contributors
  (e.g. assuming it means "adds flat XP" rather than "stacks its
  percentage with siblings before applying once") — mitigate with a clear
  docstring on `MultiplierComponent`/`combine_multipliers`.
- Frontend renderer shipped out of step with the backend shape change,
  showing wrong/incomplete numbers on new completions — sequenced as its
  own explicit step (6), not assumed to fall out automatically.

---

## 8. Open questions

- Should Player-scoped `XpModifier` consumption be activated now (option a
  in §4), or stay deliberately out of scope (option b, recommended)?
- Should `XpModifier.mode` be admin-editable (likely yes, given rows
  already look ops-managed) or code-only for now?
- Does the skill-link bonus belong in the additive or multiplicative
  bucket? Not decided here — a balance call for step 5.
- Should `reward_breakdown` carry an explicit shape/version marker so the
  frontend can distinguish pre-pipeline historical records from
  post-pipeline ones without inferring from key presence?
