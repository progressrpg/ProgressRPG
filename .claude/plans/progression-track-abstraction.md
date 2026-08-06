# Progression Abstraction — Analysis & Migration Plan

Analysis only — no code changes in this document's scope. Covers PR #696
(`epic/role-skill-taxonomy-and-points-economy` → `development`), which implements
issues #688–#692 and #299.

---

## 1. Current model inventory (progression-relevant)

- **`users.models.Person`** (abstract base of `Player` and `Character`): `xp`,
  `xp_next_level`, `xp_modifier`, `level`. Owns the level-up loop (`add_xp`),
  the threshold formula (`_ap_threshold_for_level` = `100 * (level + 1)`),
  a monotonic-total reconstruction (`total_ap_earned`), and multiplier lookup
  (`get_xp_multiplier`, reading `XpModifier` rows via `active_link`).
- **`gameplay.models.XpModifier`**: scoped (`PLAYER`/`CHARACTER`) timed
  multiplier rows, read by `Person.get_xp_multiplier`.
- **`progression.points`**: `base_rate()`, `xp_for_duration()` (flat skill XP),
  `xp_mastery_multiplier()` (AP multiplier driven by accumulated skill XP).
  Both pull tunables from `core.models.GameSettings`.
- **`progression.models.TimeRecord`** (abstract; `PlayerActivity`,
  `CharacterActivity`): `duration` is the sole stored fact; AP/XP are computed
  live via `get_xp_reward_summary()` and snapshotted into `reward_breakdown`
  (display-only) on completion, then applied via `Person.add_xp`.
- **`progression.models.Role` / `SkillGroup` / `SkillDefinition` /
  `CharacterSkill`**: skill "proficiency" is a *derived* number
  (`_character_skill_duration` → `xp_for_duration`), summed live from
  completed `CharacterActivity` + `CharacterActivityArchive` rows. No
  persistent ledger, no level — just a scalar compared against
  `min_proficiency` for gating.
- **`locations.models.PopulationCentre.village_points`**: sums residents'
  `total_ap_earned` directly — a world-economy feature reading Person's
  internal reconstruction math.
- **`gameplay.models.Currency` / `CurrencyAccountBase` /
  `PlayerCurrency` / `CharacterCurrency`**: an *existing*, working pattern for
  "named ledger type + per-owner account" (used for coins / link points).
  Notably not used for AP/XP today, but structurally the closest analogue to
  what a `ProgressionTrack` needs (see §3).

---

## 2. Conflated concepts

1. **Two different "XP"s share a name.** `Person.xp` is really *Activity
   Points* (AP) — a universal currency that drives leveling. "Skill XP"
   (`xp_for_duration`, `CharacterSkill.total_xp`, `skill_xp_gained` in reward
   breakdowns) is a separate quantity: never stored, never leveled, only
   summed and used for gating/mastery. They share code (`base_rate`,
   `xp_for_duration`) and vocabulary but are different currencies with
   different lifecycles.

2. **One leveling formula, hardcoded on an abstract base, applied to two
   semantically different entities.** `Player.level` currently has no
   gameplay effect (display only). `Character.level`/`total_ap_earned` feeds
   `village_points`. Both are forced through the same
   `_ap_threshold_for_level` curve with no way to diverge without touching
   `Person` itself.

3. **A second, independent progression system already exists and doesn't
   reuse Person at all.** Role/SkillGroup proficiency is "accumulate a scalar
   from duration, gate on a threshold" — conceptually a progression track —
   but it's implemented as a live SQL aggregation with its own bespoke gating
   (`min_proficiency`), not through any shared abstraction with AP/level.

4. **Reward computation and reward application are fused into the record
   models.** `get_xp_reward_summary()` (pure function of duration + settings)
   and the act of crediting it (`Person.add_xp`, called from `_finish`/
   `complete()`) live in the same model methods. Fine with one track; already
   awkward for skill XP, which is credited *nowhere* — it's recomputed from
   scratch every time it's read, because there's no ledger to credit it to.

5. **World/economy code reaches into Person's internal reconstruction math.**
   `village_points` calls `total_ap_earned`, which exists specifically to undo
   `add_xp`'s lossy per-level `xp` reset. If AP were stored as a running total
   directly (as `CurrencyAccountBase.earned` already does for currencies),
   this reconstruction wouldn't be needed at all.

6. **`XpModifier.Scope.PLAYER` is defined but effectively dead.** Only
   `CharacterActivity.get_xp_reward_summary` calls `character.get_xp_multiplier()`;
   `PlayerActivity` uses a separate, unrelated multiplier path
   (`Player.get_activity_xp_multiplier` for premium + `task_activity_xp_multiplier`).
   So "the same multiplier mechanism applies to both Person subclasses" is
   aspirational, not actually true today — another sign the abstraction is
   Character-shaped, not Person-shaped.

---

## 3. Proposed abstraction

### Chosen approach: extend the existing Currency pattern, not `GenericForeignKey`

The codebase already has the exact shape needed — `Currency` (type
definition) + `CurrencyAccountBase` (abstract earn/spend ledger) +
`PlayerCurrency`/`CharacterCurrency` (concrete per-owner accounts,
`unique_together(owner, currency)`). No `GenericForeignKey` is used anywhere
in this codebase (checked); introducing one here would be a new pattern for a
problem the Currency split already solves. A `ProgressionTrack` should mirror
it directly:

- `ProgressionTrackDefinition` (mirrors `Currency`): `code`, `name`, and the
  *curve* parameters currently hardcoded in `Person`/`GameSettings` (e.g.
  `base_threshold`, `growth`, or a `curve_kind` choice) — so different tracks
  (player AP, character AP, a future prestige track) can diverge without code
  changes, the same way `GameSettings` already externalizes tunables like
  `xp_mastery_scale`.
- `ProgressionTrackAccountBase` (abstract, mirrors `CurrencyAccountBase`):
  `total_earned` (monotonic, replaces the `total_ap_earned` reconstruction —
  store the running total directly instead of deriving it from `level`+`xp`),
  plus `level` and a `earned_toward_next_level` property computed from
  `total_earned` and the track's curve. No `spent` field — AP/XP are never
  spent today, so don't carry currency semantics that don't apply.
- `PlayerProgressionTrack(player FK, track FK)`, `CharacterProgressionTrack
  (character FK, track FK)`: concrete accounts, same shape as
  `PlayerCurrency`/`CharacterCurrency`.

Not every track needs "level" to mean anything (skill XP tracks would use the
same account row but never surface `level` in the UI) — the level/threshold
computation is a property derived from `total_earned` + curve, not a required
piece of every track's identity.

**Alternative considered — keep `Person`, extract only the curve policy.**
Smaller change: pull `_ap_threshold_for_level`/`total_ap_earned`/
`get_xp_multiplier` out of `Person` into a standalone policy object each
subclass configures. Cheaper, lower migration risk, but doesn't solve
conflation #3/#4 — skill XP still has nowhere to live, so Role/SkillGroup
proficiency stays a second, un-unified system. Rejected as the end state, but
this is exactly **Phase 1** below — it's the low-risk first step that also
happens to be a prerequisite for Phase 2 (can't split AP from skill XP
cleanly while the curve math is still tangled inside `Person`).

**Alternative considered — a single generic `ProgressionTrack` model with
`GenericForeignKey` owner.** More flexible (one table for all trackable
entity types), but introduces a pattern the codebase doesn't use anywhere
else, loses the FK-level `unique_together` constraint Django gives
`PlayerCurrency`/`CharacterCurrency` for free, and is harder to query
efficiently (`select_related` doesn't cross a GFK). Rejected — reuse over new
abstractions, and the Currency pattern already covers the "which concrete
owner types exist" question with two FKs, not an open-ended content-type.

### Phased migration

**Phase 1 — decouple the curve from `Person`, no schema change.**
Extract `_ap_threshold_for_level`, `total_ap_earned`, `get_xp_multiplier`
into a small `progression` service/helper `Person` delegates to. Behavior-
identical; purely a seam so Phase 2 can swap what backs `.xp`/`.level`
without touching every call site simultaneously. Also formalizes "AP" as the
name in code (rename internal helpers away from generic `xp` where they mean
AP specifically), addressing conflation #1 without a data migration.

**Phase 2 — give skill XP an actual ledger.** *(corrected — see §8)*
Both owners already have a live-derived skill XP source that's never
persisted: `CharacterSkill.total_xp` (via `SkillDefinition`, summing
`CharacterActivity`/`CharacterActivityArchive` duration) and
`PlayerSkill.total_xp` (inherited from the abstract `Skill.total_xp`, summing
linked `PlayerActivity` duration) — `PlayerSkill` is a real, user-facing
model (own viewset/serializer, displayed in the frontend `SkillsPanel`), not
a stub. The narrower true gap is that no `player_total_skill_xp()` aggregate
feeds a player's own AP mastery multiplier the way `character_total_skill_xp`
does for characters (`PlayerActivity.get_xp_reward_summary` hardcodes
`xp_mastery_multiplier(0)`).

Because `PlayerSkill`/`CharacterSkill` are already one row per (owner,
skill) — the exact granularity a skill-XP ledger needs — Phase 2 is likely
**not** "introduce a new `ProgressionTrack`-shaped table," but "add a
persisted `total_earned` field + a credit method directly onto the existing
`PlayerSkill`/`CharacterSkill` models," reusing what's already there instead
of inventing a new abstraction for it. `Role.proficiency_for`/
`SkillGroup.proficiency_for`/`SkillDefinition.is_unlocked_for` (character
side) switch from live duration aggregation to reading the credited total;
a `player_total_skill_xp()` aggregate can then be added for the player-side
mastery multiplier gap. Needs a proper pass at Phase-2 planning time rather
than deciding the final shape here.

Also worth cleaning up in the same pass: `Skill.level` (inherited by
`PlayerSkill`) is a stored field that's never written anywhere in
non-migration code — dead, same class of issue as `Person.xp_modifier`.

**Phase 3 — migrate AP itself, if still justified.**
Once Phase 2 is proven, decide whether `Person.xp`/`level` should also move
onto `PlayerProgressionTrack`/`CharacterProgressionTrack` (data migration:
`total_earned = total_ap_earned`, recompute `level` from the curve) or stay
as-is now that Phase 1 already isolated the curve logic. Not committing to
this now — do it only if a second AP-like track actually materializes (the
plan doc that requested this analysis is itself the trigger to revisit).

---

## 4. Which parts of the current PR depend on `Person.xp`/`level`

**Directly coupled** (would be rewritten if AP moves to a track model):
- `progression/models.py`: `PlayerActivity.get_xp_reward_summary`/`complete`,
  `CharacterActivity.get_xp_reward_summary`/`_finish`/`complete_now`/
  `complete_past`
- `progression/points.py`: `xp_mastery_multiplier` (feeds the amount passed to
  `add_xp`)
- `users/models.py`: `Person` itself, `Player.add_activity`
- `character/models/character.py`: `Character` itself
- `character/services/character_services.py`: `character_apply_quest_results`
  (`character.add_xp`)
- `users/services/login_services.py`: `handle_first_login_of_day`
  (`player.add_xp`)
- `locations/models.py`: `PopulationCentre.village_points`
  (`total_ap_earned`)
- Display/reset call sites: `api/views.py`, `users/achievements.py`,
  `character/serializers.py`, `users/serializers.py`,
  `users/tasks.py` (account-deletion wipe), `users/management/commands/
  seed_playwright_user.py`

**Not coupled to `Person`'s internals** — these only assume "the character
has *some* `add_xp`-shaped sink", not any particular storage:
- #688 Role/skill taxonomy (`Role`, `SkillGroup`, `SkillDefinition`,
  `CharacterRole`, `CharacterSkill`) — already derives proficiency from
  `TimeRecord.duration`, not from `Person`, so it's forward-compatible with
  Phase 2 with a contained rewrite (3 functions in `progression/models.py`).
- #690 `ActivityDefinition`/`CharacterActivity` field rewrite, `work_activities_for`
- #689 `Activity`/`SuggestedActivity`/`PlayerActivity` FK rework
- #299 `CharacterActivityArchive` + compaction task

**Conclusion:** only #691 (points economy rework) is *about* `Person.xp`/
`level`; everything else in the current PR is structurally independent and
doesn't need to be delayed or rewritten for a future `ProgressionTrack`
introduction — only the bounded call-site list above would need updating
later, which is a mechanical follow-up, not a redesign.

---

## 5. Splitting the mega PR

The existing commits on this branch already align close to 1:1 with the
sub-issues, so this is a **stacked-PR cut**, not a rewrite — land the same
commits as a sequence of PRs against `development`, each based on the
previous one's merged branch, in dependency order:

| PR | Commit(s) | Content | Depends on |
|----|-----------|---------|-------------|
| A | `0429e692` | #688 Role/skill taxonomy | — |
| B | `a9a3b883` | #689 Player-side Activity catalog | — (parallel to A) |
| C | `6b3710c8` | #690 ActivityDefinition + CharacterActivity rewrite (incl. `CharacterQuest`→`QuestTimer` retarget) | A |
| D | `85695fc6` | #692 Re-enable daily generation | C |
| E | `8dc46932` (+ plan doc `d19a9f5f`) | #299 Compaction | C |
| F | `0f2d132c` | #691 Points economy rework | A, C |
| — | `8cbd6e74` | Security hardening (admin-only writes on new catalog viewsets) | rides with whichever of A/C introduces the affected viewsets, or its own small follow-up |
| — | `7072cb19`, `52000beb` | Unrelated fixes (pre-existing black formatting, road-connection test) | land independently, not part of this epic at all |

Notes:
- C's `CharacterQuest` deletion/`QuestTimer` retarget is a distinct,
  discovered-mid-issue cleanup — worth calling out as its own commit/paragraph
  in C's PR description even if not a separate PR, since it's unrelated to
  `ActivityDefinition` itself.
- **F (#691) is the one to hold back**, not the others. Recommend either:
  (a) merge A–E now (they're independently correct and tested), and land F
  once Phase 1 of §3 is done underneath it — F gets written once, directly on
  the decoupled curve, avoiding a second pass; or
  (b) merge F as-is now (it already works, is tested, and Phase 1's extraction
  is a behavior-preserving refactor that can follow it without forcing a
  rewrite). Both are defensible; (a) avoids touching `village_points`/login
  rewards/quest completion twice, (b) ships value sooner. This is a judgment
  call on risk appetite, not a technical blocker either way — flagging as an
  open question below rather than deciding it here.

---

## 6. Open questions

1. ~~Hold F (#691) until Phase 1 lands underneath it, or ship it now and layer
   Phase 1 on top afterward?~~ Resolved — see §7: land Phase 1 (extraction,
   no schema change) before F, do not do the full model swap (Approach B)
   before F.
2. Does `Player.level` need to do *anything* gameplay-visible, or is it
   purely cosmetic? If purely cosmetic, it's a candidate to drop from the
   track-abstraction scope entirely rather than modeled as a first-class
   track.
3. Is a "curve config on the track definition" (Phase 3, §3) actually wanted,
   or is one shared curve for all AP-like tracks fine indefinitely? Affects
   how much of `GameSettings`'s tunables should move onto
   `ProgressionTrackDefinition` vs. stay global.
4. Should skill XP (Phase 2) get per-skill decay/compaction parity with
   `CharacterActivityArchive`, or is summing the archive at read time
   (current behavior) fine once it's also backed by a ledger?

---

## 7. Approach A vs B — deeper comparison

Prompted by: should `ProgressionTrack` be introduced *now*, moving AP out of
`Person.xp` before F (#691) lands, rather than after?

### 7.1 Reframing the concern

The worry is "don't integrate #691 with a system we already want to
replace." But `Person.xp`/`level` isn't new — it's the pre-existing storage
for the app's whole leveling system, already live in production before this
epic. The current non-test consumers of `.xp`/`.level`/`total_ap_earned`/
`add_xp`/`xp_next_level`:

`progression/models.py`, `progression/points.py`, `users/models.py`,
`character/models/character.py`, `character/services/character_services.py`,
`users/services/login_services.py`, `locations/models.py`, `api/views.py`,
`users/achievements.py`, `character/serializers.py`, `users/serializers.py`,
`users/tasks.py`, `users/admin.py`, `users/management/commands/
seed_playwright_user.py` — **13 files**, almost none of them written by this
epic (achievements, admin, login rewards, account deletion, village points,
API serializers all predate it). Plus 6 test files assert on these fields
directly: `character/tests/test_models.py`, `gameplay/tests/
test_activity_timer_premium.py`, `gameplay/tests/test_models.py`,
`locations/tests/test_population_centre_views.py`, `users/tests/
test_management_commands.py`, `users/tests/tests.py`.

F (#691) adds exactly **two** new call sites into that existing surface
(`CharacterActivity._finish` calling `character.add_xp`, and `PlayerActivity.
complete` → `Player.add_activity` → `add_xp`, the latter arguably a bugfix of
a call that should already have existed). Blocking F to avoid "integrating
with what we want to replace" saves rewriting 2 call sites out of ~13+6 —
the other files depend on `Person.xp` regardless of whether F ships before or
after a `ProgressionTrack` swap. **The debt is pre-existing and
timing-independent; F does not materially deepen it.**

Also found in passing: `Person.xp_modifier` (the field, not the `XpModifier`
model) is dead — set in a serializer/admin and reset by a seed command, never
read by `get_xp_multiplier` or anywhere else. Whenever the swap happens, this
field should be dropped rather than carried into the new model.

### 7.2 Approach A vs B

| | **A — Minimal** | **B — Full** |
|---|---|---|
| Schema change before F | None | New model(s) + data migration + column drop |
| Files touched before F | ~2-3 (the curve extraction itself) | ~13 non-test + 6 test files, in the middle of a 118-file epic |
| API/serializer contract | Untouched | `xp`/`level`/`xp_next_level`/`xp_modifier` become computed fields (shape can stay the same on the wire) |
| Solves skill-XP-has-no-ledger (§2 conflation #3) | No — deferred to Phase 2 either way | No — B as scoped ("move AP out of Person.xp") doesn't touch skill XP either |
| Risk of a second migration later | Low — Phase 2 adds a genuinely new ledger, not a reshape of this one | Real, if the AP-only shape built now doesn't match what skill XP needs later (see §7.4) |
| Ships F | Immediately after a short, low-risk refactor | After a full storage migration completes and is verified |

### 7.3 Migration complexity of B

1. **New model(s)** for the AP ledger (design in §7.4).
2. **Three-step data migration** — this repo already has a proven template
   for exactly this shape of change, used twice already in this same branch
   (`0006`→`0008` for the role/skill taxonomy, `0012`→`0014` for
   `reward_breakdown`/`xp_gained`): add the new table → backfill from
   existing columns (`total_earned = total_ap_earned`, `level = level`) →
   drop the old columns in a later migration once the backfill is verified.
   Not a novel risk for this codebase, but real work, and it's working with
   real production data (`Person.xp`/`level` already accrue for live
   players/characters today).
3. **Concurrency**: today, `add_xp` mutates an in-memory `Person` instance
   (`self.xp += amount`) under `@transaction.atomic` but without
   `select_for_update` — a pre-existing lost-update race if two completions
   land concurrently for the same owner. Moving the write to a related row
   doesn't fix this by itself; if B is done, it's a natural point to add
   `select_for_update()` on the track row rather than carry the race forward
   unexamined.
4. **Every call site in the 13-file list** swaps `.add_xp(x)` /
   `.total_ap_earned` / `.xp` / `.level` for the new accessor.
5. **Serializers** (`PlayerSerializer`, `CharacterSerializer`): `xp`/
   `xp_next_level`/`xp_modifier`/`level` go from direct model fields to
   `SerializerMethodField`s reading through the track — same JSON keys
   achievable, so frontend (`Infobar`, `Account`, `useAccountPage`,
   `types/domain.ts`) doesn't have to change if this is done carefully.
6. **Admin** (`users/admin.py`, two separate `ModelAdmin` classes reference
   `level`/`xp`/`xp_next_level`/`xp_modifier` in `list_display`/
   `readonly_fields`/`fieldsets`) needs related-field display instead.
7. **Test rewrite** bounded to the 6 files that assert on the literal
   attributes — tests that only exercise leveling through public methods
   (e.g. `character.complete_quest(...)`) don't need to change if those
   method names are preserved.

### 7.4 Smallest viable `ProgressionTrack` (if/when B happens)

Avoid two things that would be over-engineering for what's known today:

- **No `ProgressionTrackDefinition` authoring table.** The set of tracks is
  small and code-defined (today: just "ap"), not admin-authored content —
  same reasoning the codebase already applies to `ActivityDefinition.Kind`
  and `XpModifier.Scope` (`TextChoices`, not a table). Curve constants
  (threshold formula, mastery cap) stay on `GameSettings`, consistent with
  where `xp_mastery_scale`/`xp_mastery_multiplier_cap` already live.
- **No `GenericForeignKey`.** Not used anywhere in this codebase; two
  concrete FKs (player/character) matches every other owner-scoped pattern
  here (`PlayerCurrency`/`CharacterCurrency`, `PlayerSkill`/`CharacterSkill`).

But **do** use a `track` choice field + `unique_together(owner, track)` from
day one, rather than a bare `OneToOneField` to the owner for "ap" alone. A
`OneToOne` would be marginally simpler today but guarantees a second
migration (`OneToOne` → `FK` + `unique_together`) the moment skill XP (Phase
2) needs a second row per character — and this codebase's own `Currency`
model already committed to the FK+code shape for exactly two rows
(`coins`, `link_points`) rather than special-casing the first one. Minimal
shape:

```
class ProgressionTrackBase(models.Model):
    class Track(models.TextChoices):
        AP = "ap", "Activity Points"
    track = models.CharField(max_length=20, choices=Track.choices, default=Track.AP)
    total_earned = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True
    # add_xp(), xp_next_level, get_xp_multiplier() moved here unchanged from Person

class PlayerProgressionTrack(ProgressionTrackBase):
    player = models.ForeignKey("users.Player", on_delete=models.CASCADE, related_name="progression_tracks")
    class Meta:
        unique_together = ("player", "track")

class CharacterProgressionTrack(ProgressionTrackBase):
    character = models.ForeignKey("character.Character", on_delete=models.CASCADE, related_name="progression_tracks")
    class Meta:
        unique_together = ("character", "track")
```

This still requires the full call-site/serializer/admin/test rewrite in
§7.3 — the choice-field shape avoids an extra *schema* migration later, it
doesn't avoid the rewrite itself, which is inherent to moving off `Person`
at all.

### 7.5 Recommendation

**Do A, not B, before landing F.** Concretely:

- Land Phase 1 (§3) now: extract `_ap_threshold_for_level`/`total_ap_earned`/
  `get_xp_multiplier` out of `Person` into a clearly-AP-named helper, with a
  method surface that already matches §7.4's future `ProgressionTrackBase`
  (`add_xp`, `total_earned`-style total, `level`) — even though it's not a
  model yet. This is a same-file refactor, no migration, no serializer/admin/
  test churn, and it directly addresses conflation #1 (the "xp" naming
  collision) without needing to decide the final schema yet.
- Land F (#691) on top of it.
- Do the actual `ProgressionTrack` model + data migration (B) only when
  Phase 2 gives it a second real consumer (skill XP), so the 13-file/6-test
  rewrite happens **once**, covering both AP and skill XP together, instead
  of once now for AP alone and potentially again later if the AP-only shape
  needs adjusting to fit skill XP.

Why not B now: the stated concern (avoiding double integration work) doesn't
actually hold up under §7.1 — F's contribution to the `Person.xp` surface is
2 call sites out of ~19 files, so sequencing F before or after B changes
almost nothing about the eventual rewrite's size. What B-now *does* cost is a
full production data migration and a 19-file/6-test rewrite, done in the
middle of an already 118-file epic, designed against a single known track
(AP) with no second consumer yet to validate the chosen shape against — the
exact "unnecessary abstraction" / "architectural drift" risk the planning
template flags. B is worth doing once skill XP is ready to move onto the same
mechanism; it is not worth doing to unblock F specifically.

---

## 8. Correction — players already have a skill XP source

An earlier version of §3 claimed "Player doesn't need [a ledger] yet -
players have no skill XP source", citing a comment in `progression.points`.
That was wrong. `PlayerSkill` (a real, user-facing model — own viewset/
serializer, `total_xp` displayed in the frontend `SkillsPanel`) inherits
`total_xp` from the abstract `Skill` base, live-derived from linked
`PlayerActivity` duration via `xp_for_duration` — the same mechanism
`CharacterSkill.total_xp` uses for characters. The `progression.points`
comment actually being referenced is narrower: no `player_total_skill_xp()`
aggregate feeds a player's *own AP mastery multiplier* the way
`character_total_skill_xp` does for characters — a real gap, but not "no
skill XP."

This also reframes Phase 2's likely shape: since `PlayerSkill`/
`CharacterSkill` are already one row per (owner, skill) — the granularity a
skill-XP ledger needs — Phase 2 is more likely to be "persist a total on the
existing skill models" than "introduce a new `ProgressionTrack` table." §3's
Phase 2 description above has been corrected accordingly; the final shape
still needs a proper look at Phase-2 planning time.
