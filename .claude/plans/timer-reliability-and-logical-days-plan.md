# Timer reliability: server-derived liveness, auto-pause, and logical days

Supersedes `timer-liveness-server-side-heartbeat-plan.md` and `timer-auto-pause-instead-of-autocomplete-plan.md` (both in git history). They turned out to be one piece of work: pausing an interrupted session is only safe if a paused session can still be attributed to the right day, and attributing to the right day is only meaningful once sessions stop being force-submitted at arbitrary moments.

## The three problems

1. **Liveness is judged by page JS.** `Player.last_seen` is stamped by a `setInterval` in the player's tab, which browsers throttle when backgrounded and stop when the device sleeps. The sweep that reads it therefore mistakes "tab in the background" for "player gone". (Root cause of the reported timers stopping at 7m35s / 9m11s; PR #804 widened the thresholds but left the signal in the browser.)
2. **The response to "player gone" is destructive.** Auto-complete force-submits the session — irreversibly, since it awards XP, writes a `PlayerActivity`, and fires daily-goal and streak logic. A wrong guess costs the player their session.
3. **"Which day did that count for?" has no single answer.** Attribution is by `completed_at` calendar date, computed against whichever timezone happens to be active — which differs between HTTP requests and Celery tasks (see 4f). A night-owl session at 23:00 lands on tomorrow; a session auto-paused on Tuesday and resolved on Friday would count for Friday.

Together these compound: an unreliable verdict triggers an irreversible action whose bookkeeping lands on the wrong day.

## 1. High-level strategy

Three changes, in dependency order, each independently useful:

**A. Move liveness into the server.** Daphne already sends a websocket protocol-level ping every 20s and closes any connection that doesn't pong within 30s (`--ping-interval` / `--ping-timeout`, defaults 20/30, wired to autobahn's `autoPingTimeout` in `daphne/server.py`). Protocol pings are answered by the browser's network stack, not by page JS, so they survive throttling and freezing. Have `TimerConsumer` stamp `last_seen` for as long as the socket is open, then delete the client heartbeat. Presence becomes "an ASGI process is holding a socket for this player", which is what the sweeps already assume it means.

**B. Pause instead of complete.** Bank the elapsed time, stop accruing, let the player resolve it on return. A wrong verdict now costs a resume click. This is the highest safety-per-unit-of-risk change here, and it substantially lowers the stakes of A — which is why A is no longer urgent enough to go first.

**C. Give the player a logical day.** One session belongs to exactly one day, chosen by when it *started*, where a day runs from the player's configurable `day_start_time` (default 04:00) in their own timezone. This is what makes B safe for streaks, and it fixes a class of existing bugs on its own.

Order: **C → B → A.** C is a prerequisite for B not breaking streaks. B removes the sharp edge. A removes the false positives that make the sharp edge get hit.

## 2. The day-boundary design (the substantive decision)

### Don't split sessions at the boundary

Splitting is superficially tidier for streaks and worse in every other respect:

- It breaks the one-session-one-record invariant. `duration` on `PlayerActivity` is the sole source of truth for AP/XP (`progression/points.py`), so splitting means either two rows (doubling timeline entries, halving what reads as one achievement) or one row plus split-aware arithmetic in *every* aggregation — daily goals, streaks, timeline, metrics.
- It is less accurate in the way that matters. For an ADHD-focused app, "one 2-hour deep work session" is the achievement; rendering it as two 1-hour sessions actively undercuts the product.
- With a 04:00 cutoff, boundary crossings become rare — almost nobody is working *through* 4am. **That is the real prize of the cutoff: it doesn't just relabel the edge case, it mostly eliminates it.**

### Key on `started_at`, not `completed_at`

Current behaviour attributes by `completed_at`. Change it to `started_at`:

- It matches what people mean. "I worked Tuesday night" is about when you sat down.
- It is stable under pause/resume. `ActivityTimer.start()` sets `activity.started_at` only when it is `None`, so it already survives any number of pause/resume cycles — it is genuinely "when you began".
- **It is what makes auto-pause safe.** Under `completed_at`, a session auto-paused Tuesday and resolved Friday counts toward Friday's goals. Under `started_at`, it counts for Tuesday, where it belongs. This is precisely the seam between the two original plans.

Consequence to accept: a logical day's goals can be completed retroactively (a session started Tue 23:00 and submitted Wed 01:00 awards *Tuesday's* goal at 01:00). `DailyGoalAward` is already keyed `(player, date)` with a unique constraint, so idempotency holds; the badge just needs to be computed for the current logical day while awards may land on a past one.

### Stamp the logical date at start, don't compute it at read time

Store `logical_date` (a `DateField`) on `PlayerActivity`, written when `started_at` is first set.

- **Immutable history.** A player who later changes their cutoff or timezone doesn't have their past re-labelled, and a streak can never retroactively break because of a settings change. For a motivational mechanic that property is worth more than theoretical purity.
- **Trivial aggregation.** Every day-based query becomes an indexed equality/`IN` on one column, instead of a per-player half-open range over `started_at` (which a cutoff + per-player timezone otherwise forces).
- **No "what timezone were they in last March?" problem.**

The alternative — deriving ranges at query time from the current setting — is more "correct" in the sense that it always reflects the present configuration, but that is the wrong kind of correct here, and it makes every grouped query expensive. Recommend storing.

### Naming the logical day — one thing to confirm

A logical day with a 04:00 cutoff spans e.g. Tue 04:00 → Wed 04:00. The convention question is what that day is *called*, and the plan assumes **it is named for the calendar date it starts on** (that span is "Tuesday").

Under that convention, your example resolves differently from how you stated it:

| Session | Cutoff 04:00, named by start | Named by end |
|---|---|---|
| Tue 23:00 → Wed 01:00 | **Tuesday** | Wednesday |
| Wed 10:00 → Wed 11:00 | **Wednesday** | Thursday |

Named-by-start is what actually solves the night-owl problem: your late Tuesday work keeps *Tuesday's* streak alive, which is the point. Named-by-end shifts every ordinary daytime session a day forward — Wednesday morning's work would count as Thursday — which is almost certainly not intended. **Assumption: named by start.** If you did mean the span to be called Wednesday, it is a one-line change in the helper, but check the second row of that table first.

### One definition, one helper

The day logic is currently scattered and inconsistent: `timezone.localdate()` in `daily_goals.py`, `timezone.localtime(ts).date()` in `UserLogin`, and `timezone.now().date()` — a **UTC** date regardless of the player — in `progression/views.py:253`. New `progression/day_boundaries.py` owns:

- `logical_date_for(player, moment) -> date`
- `logical_day_bounds(player, day) -> (start, end)`
- `current_logical_date(player) -> date`

Every day-based query routes through it. **This is the actual deliverable of phase C** — the settings field is trivial by comparison.

## 3. Files likely to change

**Phase C — logical days**
- `users/models.py` (exists) — `day_start_time = TimeField(default=time(4, 0))` on `CustomUser`, next to the existing `timezone` field.
- `users/migrations/00XX_*` (new) — the field.
- `progression/day_boundaries.py` (new) — the three helpers above. The one new module in this plan; justified because three apps need one shared answer.
- `progression/models.py` (exists) — `logical_date` on `TimeRecord` (nullable, indexed with `player`); stamped from `started_at`.
- `progression/migrations/00XX_*` (new) — column + index + backfill from existing `started_at`/`completed_at` at the default cutoff.
- `progression/daily_goals.py` (exists) — query `logical_date` instead of `completed_at__date`; `DailyGoalAward.date` becomes a logical date.
- `progression/views.py` (exists) — replace the UTC-date filter at line 253.
- `users/models.py` `UserLogin` (exists) — `local_date()` / `current_login_streak` / `max_login_streak` / `annotate_first_of_day` move onto logical dates.
- `gameplay/models.py` (exists) — `ActivityTimer.start()` stamps `logical_date` alongside `started_at`; the `complete()` backfill path does the same.
- `progression/serializers.py`, frontend activity-timeline grouping (exist) — group by `logical_date`.
- Account/settings UI (exists) — expose `day_start_time`.

**Phase B — auto-pause** (unchanged from the superseded plan; summarised)
- `frontend/src/hooks/useActivityTimer.ts`, `components/ActivityInput/useActivityInput.ts`, `components/UnifiedTimerHome/UnifiedTimerHome.tsx`, `types/timers.ts` — make `paused` a first-class state with Resume / Submit / Discard.
- `gameplay/tasks.py`, `gameplay/consumers.py` — pause via `pause_server_timers()` instead of completing; rename the tasks.
- `gameplay/views.py` — `set_activity` returns 409 against a paused timer holding banked time.
- `server_management/management/commands/pause_timers.py` — fix the `status="Active"` filter.
- `progress_rpg/celery.py` + a cleanup migration — renamed beat entry; `DatabaseScheduler` does not remove stale `PeriodicTask` rows.

**Phase A — server-derived liveness** (unchanged; summarised)
- `gameplay/consumers.py` — periodic `last_seen` stamp task, cancelled and awaited on disconnect.
- `render.yaml`, `render-staging.yaml`, `compose.yaml`, `Dockerfile` — explicit `--ping-interval 20 --ping-timeout 30`.
- `frontend/src/hooks/useWebSocketHeartbeat.ts` + test (added in #804) — delete; drop the call in `WebSocketContext.tsx`.
- `gameplay/tasks.py`, `users/tasks.py` — re-tune and re-document the thresholds.

## 4. Design decisions

**a. `started_at` over `completed_at`** — see 2. The decisive argument is the pause interaction: `completed_at` becomes "whenever the player got round to it", which is not a fact about when they worked.

**b. Store `logical_date` over computing ranges** — see 2. Immutable history is the safer property for a streak mechanic, and it keeps grouped queries cheap.

**c. Don't split sessions** — see 2. Alternative considered: split at the boundary into two records. Rejected on the invariant, the aggregation cost, and the product meaning — and largely mooted by the cutoff.

**d. Pause over complete** (phase B) — a wrong "player is gone" verdict should cost a click, not a session. Accepted cost: a player who never returns now gets *no* XP for work they did do, where auto-complete awarded it. Given the reported failure was live sessions being force-submitted, that is the right way round, but it is a product judgement.

**e. Derive presence from the socket** (phase A) — reacting to Daphne's pongs directly would be more precise, but Daphne handles ping/pong inside `ws_protocol.py` and surfaces nothing to the application. A periodic stamp from the consumer gets the same guarantee indirectly: the loop only runs while the consumer is alive, and Daphne guarantees the consumer doesn't outlive a client that stopped answering pings.

**f. Day computation takes the player explicitly, never ambient state.**
`CustomUser.timezone` exists, but `timezone.activate()` only happens in `UserTimezoneMiddleware` — i.e. only during HTTP requests. Celery tasks and websocket consumers run under `TIME_ZONE = "UTC"`. `ActivityTimer.complete()` calls `check_and_award_daily_goals` and runs in **both** contexts, so *the same player already gets different day boundaries depending on whether they pressed Submit or the server completed them for them.* This is a live bug today, independent of everything else here, and the cutoff cannot be trusted until it is fixed. Hence helpers that take `player` and read `player.user.timezone` directly rather than relying on whatever is activated.

**g. Default cutoff 04:00, per-user override.** 04:00 is late enough to catch essentially all night-owl work and early enough that almost nobody is mid-session. Users who want strict midnight can set it.

## 5. Edge cases

- **A session spanning the cutoff itself** (03:00 → 05:00). Attributed wholly to the day it started. Rare by construction, and the alternative is splitting.
- **A cutoff or timezone change** with sessions already recorded. Storing `logical_date` means history is untouched; only future sessions use the new setting. Worth saying so in the settings UI, since "my streak didn't change" could otherwise read as a bug.
- **A session started before a cutoff change and completed after.** `logical_date` is stamped at start, so it keeps the old day. Correct and unambiguous.
- **Retroactive goal completion.** A Tuesday session submitted Wednesday can complete Tuesday's goals after Tuesday ended. Bounded to that session's own logical day. `DailyGoalAward`'s unique constraint already makes it idempotent, but the badge query and the award path must agree on *which* day is being awarded.
- **Very old paused sessions.** A session started three weeks ago and resumed today still carries its original `logical_date`. Awarding a three-week-old day's goals is odd. Consider a horizon beyond which a paused session's resolution counts for the current day, or simply doesn't count for goals — see 8.
- **Manual/offline activities** (`Origin.MANUAL`) carry a user-supplied `started_at`; stamp `logical_date` from it, not from `now()`.
- **`set_activity` on a paused timer** — `new_activity()` resets `elapsed_time` to 0, so without the 409 guard, pausing *destroys* banked time instead of preserving it. The single most important test in phase B.
- **Backfill.** Existing rows need `logical_date` derived from `started_at` (falling back to `completed_at` where null) at the default cutoff and the user's stored timezone. Some historical rows will shift day versus what the UI showed yesterday.
- **Leaking the heartbeat task** (phase A) — a consumer that fails to cancel its loop keeps a departed player looking present forever, so their timer is never swept. Worse than the bug being fixed, and silent.
- **`DailyGoalAward.date` semantics change** from calendar to logical date. Existing rows are calendar dates at the old convention; decide whether to migrate or accept a one-off discontinuity.

## 6. Tests

**Logical days**
- `logical_date_for` around the boundary: 03:59 and 04:01 on the same calendar day fall on different logical days; 23:00 and 01:00 next-calendar-day fall on the same one.
- Correct under a non-UTC player timezone, and identical whether called from an HTTP request, a Celery task, or a consumer — the direct regression test for 4f.
- DST transitions in the player's timezone (a 23:00 → 01:00 session on the night the clock changes).
- `logical_date` is stamped at start and unchanged by pause/resume/complete.
- Daily goals and login streaks computed on logical dates: a 23:00 Tuesday session keeps Tuesday's streak alive; it does not also credit Wednesday.
- Backfill migration produces the expected dates for representative existing rows.

**Auto-pause**
- Both auto paths pause rather than complete; elapsed banked to the last confirmed heartbeat (`truncate_to_last_heartbeat` from #804); no XP awarded, no `PlayerActivity` completed.
- `pause()` → `start()` → `complete()` credits the sum of both segments.
- `set_activity` returns 409 against a paused timer with banked time.
- A paused session resolved days later credits its *original* logical day.
- XP modifiers deactivate on pause and reactivate on resume.
- Frontend: `resume()` continues from banked elapsed; a paused timer is not treated as "no timer"; the free-tier limit still fires for a session resumed past its cap.

**Liveness**
- The stamp task starts on connect, repeats while connected, is cancelled on disconnect, and **no stamp lands after disconnect returns**.
- A stamp raising a DB error doesn't kill the loop.
- Guard test pinning the stamp interval well below `STALE_TIMER_THRESHOLD`.

## 7. Risks

- **Shipping phase B's backend before its frontend** — turns a recoverable interruption into silent data loss via `set_activity`. The phase order and the server-side 409 both exist for this; they must not be collapsed into one PR.
- **Treating `isActive` as one concept.** `useActivityInput` derives `isActive = status === "active"` and uses it for two different questions ("is a session in progress" vs "is it ticking"). The likeliest frontend bug is a missed call site.
- **Leaving one day computation on the old convention.** A single stray `localdate()` or `completed_at__date` and the badge disagrees with the streak. Grep for all of them; there are at least four today, and one is already wrong (UTC).
- **Backfill drift.** Getting the backfill subtly wrong silently rewrites history for every existing player. Dry-run it against production-shaped data and eyeball a sample of boundary-crossing rows.
- **DST.** Adding a fixed offset instead of doing the arithmetic in the player's zone gives an off-by-one-hour boundary twice a year. Use `ZoneInfo` and localised datetimes throughout; never `timedelta`-shift a UTC instant to fake a local day.
- **Forgetting the XP-modifier pairing** — calling `timer.pause()` directly instead of `pause_server_timers()` leaves the online boost running against a paused session.
- **Losing `truncate_to_last_heartbeat`** in the pause rewrite — `Timer.pause()` → `apply_elapsed()` credits to `now()`, silently banking the whole detection window as worked time.
- **Missing the beat-schedule cleanup**, leaving a `PeriodicTask` row pointing at a renamed task: the sweep stops running, quietly.

## 8. Open questions

1. **Day naming.** Confirm the table in section 2 — a 04:00-cutoff day spanning Tue 04:00 → Wed 04:00 is called Tuesday. Your example described it as Wednesday, which the second row suggests isn't what you want.
2. **Is there a horizon past which a resumed session stops counting for its original day?** A three-week-old paused session awarding three-week-old daily goals is strange, but so is silently discarding real work.
3. **Should very old paused timers be closed out at all** — and if so, completed (awarding XP) or discarded?
4. **Migrate `DailyGoalAward.date` to logical dates, or accept a one-off discontinuity** at the changeover?
5. **Should the login streak also move to logical dates?** Consistency says yes (a 01:00 login is "last night"), but it widens the change beyond timers.
6. **Should a manual Pause button be exposed?** Once Resume exists in the UI it is one step away, and it is arguably the feature players would ask for. Out of scope, but the UI should be built so adding it isn't a rewrite.
7. **Should the disconnect grace period survive phase B?** Its purpose was delaying an irreversible action; pausing is cheap and reversible, so pausing immediately on disconnect may be simpler than a revocable countdown task plus its cache key and supersede guard.
