# Codebase Re-entry Audit — Design Notes

*Audit of the backend and frontend for comprehension cost, 2026-08-25. Status: findings only — no code changes were made. Remediation plan for the top five items: `.claude/plans/readability-audit-top-five-plan.md`.*

## Purpose

This is not a code-quality review. It asks one narrow question: **which patterns make this codebase expensive for a solo, non-full-time developer to re-enter after time away?** The goal is reducing the need to re-derive context — from an LLM or from a cold re-read — not general refactoring.

Purely stylistic issues (linting, formatting, import order) are out of scope. Everything here is about comprehension cost.

**Severity** means:

- **blocks re-entry** — you cannot safely change this without a full re-read of several files
- **slows re-entry** — you can, but it costs a detour
- **minor** — a papercut worth fixing when you're already in the file

## Method

Read of all non-test Python across `gameplay/`, `progression/`, `character/`, `locations/`, `economy/`, `api/`, `users/`, `core/`, `gameworld/`, plus the largest frontend modules under `frontend/src/`. Function lengths were measured with an AST pass; call sites were confirmed by grep rather than assumed.

## Two important caveats

**1. The recent code is good.** `progression/day_boundaries.py`, `progression/points.py`, `gameplay/tasks.py`, `economy/conversion.py` and `frontend/src/components/Map/Map.tsx` are genuinely well-commented — the "why" is present and the reasoning is recoverable. The comprehension cost is concentrated in the older gameplay/websocket layer and in `locations/`/`character/`, where the newer conventions haven't reached. This audit is not a verdict on the codebase as a whole.

**2. The PlayerCharacterLink websocket path is in-progress work, not dead code.** An earlier pass of this audit misread it. `TimerConsumer.set_player_and_character` currently returns `(user.player, None, None)`, which makes several downstream branches unreachable *today* — but that is scaffolding for work being re-enabled, and none of it is a deletion candidate. Specifically **not dead**, and **not to be touched as cleanup**:

- `gameplay/consumers.py:417-418` — the stub itself
- `gameplay/consumers.py:379, 397-408` — the `create_activity`/`submit_activity` branches
- `gameplay/utils.py:144-207` — `process_initiation` / `process_completion`
- `gameplay/consumers.py:295` — `schedule_online_end(self.link)`
- `frontend/src/types/enums.ts:65-71` — `ClientWebSocketAction`, including `choose_quest`/`complete_quest`

Findings that *land on* this path are still included below, and are marked **[PCL path]**. They matter more, not less, because that code is about to become reachable.

---

## 1. Working-memory load

Functions over ~40 lines, files needing 3+ others open to understand one change, and deep call chains for simple operations.

| Severity | Location | Finding |
|---|---|---|
| blocks | `gameplay/consumers.py:137-235` | `connect()` is 99 lines doing auth, duplicate-connection rejection, player/character load, Celery task revocation, heartbeat spawn, two group joins, pending-message replay and three conditional sends — and the state it sets (`self.link`, `self.activity_timer`) is read 150 lines away in `disconnect()`. |
| blocks | `character/services/behaviour_services.py:47-172` | `generate_day()` is 126 lines mixing schedule maths, RNG jitter, block assembly, overlap cleanup and a delete/recreate strategy branching on `is_past`. One change needs `character/utils.py`, `locations/services/schedule.py` and `progression/models.ActivityDefinition` open at once. |
| blocks | `character/models/character.py:274-311` + `character/services/lifecycle_services.py` | Every `LifeCycleMixin` method is a one-line delegate to a `lifecycle_*`-prefixed function. `character.get_age()` → `lifecycle_get_age()` is two hops for four lines of logic, and the prefix defeats `grep "def get_age"`. Same shape in `character/models/behaviour.py:15-61`. |
| slows | `locations/models.py:22-23, 64-79` | `find_path` / `go_home` / `go_outside` exist as a module-level wrapper *and* a `Movable` method *and* the real function in `locations/services/movement.py` — three layers to reach `random.choice(rooms)`. |
| slows | `gameplay/models.py:401-511` | `ActivityTimer.complete()` is 111 lines reaching into `progression.day_boundaries`, `progression.daily_goals`, `activity.get_xp_reward_summary`, `player.add_activity` and `self.reset()`, with four local imports. |
| slows | `api/views.py:737-812` | `FetchInfoAPIView.get()` is the bootstrap endpoint and touches metrics, timers, XP modifiers, login state, announcements, settings and online count in one method. The blast radius of a change is invisible from the file. |
| slows | `frontend/src/components/Map/Map.tsx` (890 lines) | ~15 `useEffect`s and ~10 `useMemo`s in one component; walker-animation state (`walkersRef`) is written in one effect and read in two others 100+ lines apart. Well-commented, but there's no single reading order. |
| minor | `progression/models.py` (1185 lines) | Holds skills, activities, definitions, tasks, projects, notes and ledgers. Any change starts with scrolling to find which of ~15 models owns the behaviour. |

## 2. Naming clarity

Vague or overloaded names in non-trivial paths.

| Severity | Location | Finding |
|---|---|---|
| blocks | `gameplay/tasks.py:215`, used at `gameplay/services/xp_modifiers.py:68` | `end_online_boost` is the default end-task for *every* modifier, including `activity_active` ones — the name claims it only ends the online boost. Its side effect (`behaviour.interrupt_current_activity()`) fires for both. |
| slows | `gameplay/utils.py:144, 177` | `process_initiation` / `process_completion` say nothing about what they do (start/pause the server timer, then broadcast a websocket action). The `action` parameter is passed in only to be logged. **[PCL path]** |
| slows | `progression/ap.py` vs `progression/points.py` | Two modules that each describe themselves as "the XP formula" (curve + multiplier lookup vs. base rate + mastery). Which to open for a balance change is not derivable from the names. |
| slows | `locations/services/movement.py` (throughout) | Every function takes `movable`, but the only caller ever passes a `Character` (`Journey.character`, `Character.objects.filter(is_moving=True)`). The generic name implies polymorphism that doesn't exist. |
| minor | `gameplay/models.py:105-121` | `get_elapsed_time()` / `compute_elapsed()` / `apply_elapsed()` — three near-synonyms where only the third has a side effect. |
| minor | `character/models/character.py:336` | `class CharacterManager(Manager.from_queryset(CharacterQuerySet)): pass` — an empty named class adding a lookup step and no behaviour. |

## 3. Missing "why" comments

Non-obvious game-design logic with no stated intent. **These are flagged, not explained** — the reasoning is the author's to record, and guessing at it in a doc would be worse than the silence.

| Severity | Location | What is unexplained |
|---|---|---|
| blocks | `progression/ap.py:73-81` | `get_multiplier` multiplies **every** active modifier, with no cap and no precedence. Nothing states whether unbounded multiplicative stacking is intended, or what stops `player_online` × `activity_active` × future modifiers from compounding. This is the most load-bearing formula in the game. **Resolved:** mixed additive/multiplicative stacking is planned, so the rule itself is being replaced rather than documented — see `.claude/plans/modifier-stacking-plan.md`. Worth recording that today's 1.875 is not an edge case: `player_online` and `activity_active` co-occur by construction, so that is the normal engaged-player rate. |
| blocks | `character/services/behaviour_services.py:58-99` | The entire day shape — wake 07:00 ±15min, 1h morning block, lunch at the work-window midpoint ±10min for exactly 1h, dinner 17:30 ±10min, leisure to 22:30, wind-down to 23:00 — has no rationale for any value or for the jitter widths. |
| blocks | `character/services/behaviour_services.py:102` | `rng.sample(work_activities_for(...), 2)` — exactly two distinct work activities per day, and it raises if a character has fewer than two available. No comment on why two. |
| slows | `gameplay/consumers.py:27`, `gameplay/services/xp_modifiers.py:19`, `gameplay/services/xp_modifiers.py:94` | Three unrelated grace periods — `DISCONNECT_GRACE_SECONDS = 120`, `ACTIVITY_ACTIVE_GRACE_MINUTES = 5`, `cooldown_minutes=30`. Each is documented in isolation; nothing says how they relate or why the modifier cooldown is 15× the reconnect grace. **[PCL path]** — the 30-minute cooldown is only *scheduled* from the disconnect path, so it currently never fires; re-enabling the link turns it on in practice for the first time. |
| slows | `progression/models.py:880-884` | `Decimal("0.25")` for `Kind.REST` — no comment on why rest earns quarter AP rather than zero or full. |
| slows | `progression/models.py:664-674` | Premium × task × mastery compose by multiplication in a specific order, with `task_xp_multiplier` folded in before mastery. Nothing says whether the order or the compounding is deliberate. |
| slows | `locations/services/schedule.py:20-23` | `(character_id % span) - MAX_STAGGER_SECONDS` — a deterministic stagger keyed on PK modulo 2401. Nothing explains why sequential IDs producing sequential offsets is acceptable. |
| slows | `locations/services/movement.py:45-52` | `go_home` picks a **random interior room** when one exists. Whether characters should land in a random room each time (vs. a bedroom, vs. the entrance) is undocumented. |
| minor | `locations/services/movement.py:62-86` | `radius: float = 50`, `limit = 10`, and `go_outside`'s different default `radius=100` — three unexplained tuning values in a routing function. |

## 4. Magic numbers and strings

Literals doing conceptual work without a named constant.

| Severity | Location | Finding |
|---|---|---|
| blocks | `gameplay/models.py:78-85` | `Timer.STATUS_CHOICES` is a plain list of tuples, not `TextChoices`. The literals `"active"`/`"paused"`/`"waiting"`/`"completed"`/`"empty"` are hardcoded across at least six files — `gameplay/models.py:96,131,142,152,165,175,193`, `gameplay/views.py:50,134,150,205`, `gameplay/consumers.py:270,288-290`, `gameplay/tasks.py:86,136,165,196`, `api/views.py:805`, and `frontend/src/hooks/useActivityTimer.ts`. There is no single place that tells you the state machine. (41 non-test sites; `frontend/src/types/enums.ts:34` already mirrors it as `TimerStatus`.) |
| blocks | `locations/models.py:296` | `status = models.CharField(default="active")  # e.g., active, complete` — no choices. The literals appear in `movement.py:133,158`, `tasks.py:63`, `views.py:105,258,314,359`, `serializers.py:125`, `models.py:327,393`. Worse: `locations/management/commands/place_characters.py:112` writes `status="cancelled"`, a value that neither `is_complete`, the unique constraint, nor any queryset recognises. **This one has a data-integrity question attached** — is `"cancelled"` a real third state or a bug? — so it is not a pure readability fix. |
| slows | `character/services/lifecycle_services.py:56-59`, `character/services/relationship_services.py:154-156` | `sex == "Male"` / `"Female"` comparisons and dict keys, while `Character.SexChoices` exists at `character/models/character.py:341`. |
| slows | `character/services/behaviour_services.py:58-99` | `time(7,0)`, `15`, `time(17,30)`, `10`, `time(22,30)`, `time(23,0)` inline — the day's design constants exist only as literals inside a 126-line function. |
| minor | `gameplay/consumers.py:28` and `gameplay/tasks.py:21` | `DISCONNECT_TASK_CACHE_KEY = "disconnect_task:{player_id}"` defined identically in both modules — two sources of truth for one Redis key. |
| minor | 42 sites across `locations/`, `character/` | `srid=3857` hardcoded at every `Point(...)` construction (e.g. `movement.py:187,200`, `wander.py:27`) rather than one project CRS constant. |

## 5. Inconsistent patterns

Similar things built differently, forcing per-file relearning.

| Severity | Location | Finding |
|---|---|---|
| blocks | `progression/models.py:648-687` vs `:869-907` | Two `get_xp_reward_summary()` implementations with **different key sets** (`task_xp_multiplier` vs `kind_multiplier`/`boost_multiplier`) and different semantics: the CharacterActivity one applies `character.get_xp_multiplier()` (XpModifier boosts), the PlayerActivity one does not. Which reward rules apply depends on which model you're holding, and nothing says so. |
| blocks | `locations/tasks.py:133` (`commute_tick` → `schedule.py`) vs `gameworld/tasks.py:38-50` (`sun_phase_started` → `react_to_sun_phase` → `go_home`/`go_outside`) | Two independent systems decide where a character walks, with different triggers and different destination logic. Only one is scheduled (see §7), but both are live code. |
| slows | `gameplay/services/xp_modifiers.py:169-174` vs `progression/mixins.py:121` | Player-scope `XpModifier`s (`ACTIVITY_ACTIVE_PLAYER_MULTIPLIER = 1.25`) are created, revoked and grace-extended — but the only reader of `get_xp_multiplier()` anywhere is `progression/models.py:885` (`self.character.…`), and `PlayerActivity.get_xp_reward_summary` never consults modifiers at all. Player scope is currently write-only. **Resolved: remove the write, don't wire up the read.** At player scope this modifier is tautological — it is active exactly when the player is recording, and recorded activity is the only source of player AP, so it would multiply every unit of AP it could ever apply to. That is a base-rate change wearing a modifier's clothes. `Scope.PLAYER` stays on the model for genuinely player-level modifiers (events, streaks, seasonal), which need a live read path when the first is authored. See `.claude/plans/modifier-stacking-plan.md` commit 1. |
| slows | `character/models/*` and `locations/models.py` vs `progression/`, `gameplay/services/` | Two service conventions: model-method-delegates-to-prefixed-service-function (`behaviour.generate_day()` → `behaviour_services.generate_day()`) and plain-function-called-directly (`check_and_award_daily_goals(player)`, `set_activity_active_modifiers(player, ...)`). |
| slows | `api/views.py` (APIView + `ViewSet` + `@action`), `progression/views.py` (`ModelViewSet` + queryset mixins), `locations/views.py` (bare `APIView` + `ReadOnlyModelViewSet`), `gameplay/views.py` (`ViewSet` + `@action`) | Four view idioms for CRUD-ish endpoints, with permission and queryset scoping done differently in each. |
| slows | `frontend/src/api/*.ts` vs direct `apiFetch` callers | A dedicated API layer exists (`api/tasks.ts`, `api/notes.ts`, …) *and* seven modules bypass it: `hooks/useActivityTimer.ts`, `useBootstrapGameData.ts`, `useOnboarding.ts`, `useTutorialSteps.ts`, `useMaintenanceStatus.ts`, `components/MaintenanceWatcher.tsx`, `components/TutorialModal/TutorialModal.tsx`. |
| minor | `core/models.py:243` (`AnnouncementQuerySet.as_manager()`) vs `character/models/character.py:336` (`Manager.from_queryset(...)` subclass) | Two manager idioms for the same job. |

## 6. Test coverage as documentation

Gaps where a test would let you verify your understanding without re-reading the implementation. `progression/` and `gameplay/services/xp_modifiers.py` are well covered; these are the holes.

| Severity | Location | Finding |
|---|---|---|
| blocks | `gameplay/utils.py` | `control_timers` / `process_initiation` / `process_completion` have **no direct tests** — only mocked out in `test_disconnect_grace.py:275,305,337`. This is a 60-line async path with a known unbound-variable bug (§7) and no test exercising either branch, about to become reachable. **[PCL path]** — the highest-value test gap in this audit. |
| blocks | `locations/services/movement.py:152-205` | `step_toward`'s distance-budget loop — spending one tick's budget across multiple short segments, plus the partial-segment interpolation — has no direct test. `locations/tests/test_models.py:173` only asserts it "does not raise". This is the logic the frontend walker animation must agree with. |
| blocks | `character/services/behaviour_services.py:176-280` | `sync_to_now`, `advance` and `interrupt_current_activity` have no tests; `character/tests/test_behaviour_services.py` covers only `generate_day` and `delete_day`. `interrupt_current_activity` is what `end_online_boost` fires on every modifier expiry. |
| slows | `locations/services/movement.py:12-26` | `find_path` (self-described in-code as "very dumb") is untested — nothing pins down whether it returns shortest-hop paths or just *a* path. |
| slows | `progression/ap.py:89-103` | `get_productivity` is untested despite being the "how productive is this character" signal surfaced to players. `test_ap.py` covers the curve maths only. |
| slows | `locations/services/movement.py:29-101` | `go_home` / `go_outside` have no tests; the random-room and radius behaviour is unpinned. |

## 7. Dead code and stale branches

Genuinely unused or superseded. **The PlayerCharacterLink path is excluded** — see the caveat at the top. The XpModifier/AP rename is known and in progress and is also excluded.

| Severity | Location | Finding |
|---|---|---|
| blocks | `gameplay/utils.py:120-124` | Not a stale branch — a **live bug**. `control_timers`'s invalid-mode `else` sets `result_text` and logs, then falls through to `if server_success:`, which is never assigned. An unrecognised mode raises `NameError` instead of returning `False`. Reachable as soon as `handle_client_request` starts dispatching again. **[PCL path]** |
| slows | `locations/tasks.py:103-130`, `locations/services/wander.py`, `locations/tests/test_wander.py` | `wander_tick` was replaced by `commute_tick` and explicitly disabled by `locations/migrations/0002_disable_wander_tick_periodic_task.py` — but the task, its service and its 100-line test suite all remain and still read as live. |
| slows | `progress_rpg/celery.py:28-39, 81-84, 105-109` | Four commented-out beat entries (character deaths, two pregnancy tasks, `move_characters_tick`, `precompute-sun-times`). Because `precompute_sun_times` is off, the entire sun-phase → `react_to_sun_phase` → `go_home`/`go_outside` chain and the whole `LifeCycleMixin` pregnancy/death system (`character/services/lifecycle_services.py`, `gameworld/tasks.py:90-140`) are unreachable in production while remaining fully tested and maintained. |
| minor | `character/services/behaviour_services.py:92` | `day_window(behaviour, date)` is called and its return value discarded — a no-op line in the middle of the day generator. |
| minor | `character/services/behaviour_services.py:265` | `interrupt_current_activity(behaviour, boost_ended=False)` — the parameter is never read, and the only caller (`gameplay/tasks.py:234`) doesn't pass it. |
| minor | `gameplay/models.py:148-155`, `:109-111` | `set_waiting()` has no callers anywhere; `compute_elapsed()` is referenced only from a commented-out log line at `:226`. |
| minor | `gameplay/services/timer_service.py` | Two import statements and no code. |
| minor | `api/views.py:772-773` | `"population_centre": None` and `"xp_mods": []` are hardcoded constants in the bootstrap payload, while `api/serializers.py:148-149` types them as real fields and `frontend/src/hooks/useBootstrapGameData.ts:60` still reads `info.xp_mods`. Likely placeholders for the same re-enablement — a one-line comment saying so would save the next person the trace. |
| minor | `frontend/src/hooks/useActivityTimer.ts:19, 27` | Two stale comments: the `status` comment omits `"paused"` (a load-bearing state), and `canResume`'s trailing comment ("true after auto-stop fires") describes `autoStopCompletion`, not `canResume`. |

---

## Where to start

Two plans came out of this audit.

**`.claude/plans/readability-audit-top-five-plan.md`** — five items, none of which changes observable behaviour:

1. Tests for `gameplay/utils.py` (§6) — the reason the bug below was invisible.
2. The `control_timers` `NameError` (§7) — a real bug on the path being re-enabled.
3. `Timer.STATUS_CHOICES` → `TextChoices` (§4) — mechanical but wide; the most-copied literal in the codebase.
4. The two `get_xp_reward_summary()` implementations (§5).
5. `step_toward`'s missing test (§6).

**`.claude/plans/modifier-stacking-plan.md`** — mixed additive/multiplicative modifier stacking, plus the player-scope removal and the missing `UniqueConstraint`. This is a behaviour change and is deliberately kept out of the plan above.

## Open questions

Two of the three questions this audit raised have been resolved into the modifier-stacking plan (see §3 and §5 above). One remains:

- **Is `Journey.status = "cancelled"`** (`place_characters.py:112`) a real third state or a bug? It determines whether the `Journey.status` half of the §4 finding is a readability fix or a data fix, and no plan currently covers it.
