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

**C. Give the player a logical day.** One session belongs to exactly one day, chosen by when it *started*, where a day runs from the player's configurable `day_start_time` (default 02:00) in their own timezone. This is what makes B safe for streaks, and it fixes a class of existing bugs on its own.

**D. Persist the session limit, so a bounded session doesn't need a verdict at all.** A session with a declared duration has a knowable end, so a disconnect requires no guess about the player: it runs to its declared end and completes there. Today limits exist only in the browser, so the server can't do this. Persisting them is also what a bounded/countdown timer needs as a feature in its own right (see 4m).

Order: **C → B → D → A.** C is a prerequisite for B not breaking streaks. B removes the sharp edge. D removes the need to guess for any session that declared its own end. A removes the false positives behind the remaining guesses. D and A are independent of each other and can run in parallel.

## 2. The day-boundary design (the substantive decision)

### Don't split sessions at the boundary

Splitting is superficially tidier for streaks and worse in every other respect:

- It breaks the one-session-one-record invariant. `duration` on `PlayerActivity` is the sole source of truth for AP/XP (`progression/points.py`), so splitting means either two rows (doubling timeline entries, halving what reads as one achievement) or one row plus split-aware arithmetic in *every* aggregation — daily goals, streaks, timeline, metrics.
- It is less accurate in the way that matters. For an ADHD-focused app, "one 2-hour deep work session" is the achievement; rendering it as two 1-hour sessions actively undercuts the product.
- Because attribution is by `started_at`, no cutoff value causes a split — the cutoff only decides *which* day late-night work lands on. A later cutoff captures more of it as "last night": at 02:00 a session started at 02:30 counts as the new day, where at 04:00 it would have counted as the night before. That is the whole trade.

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

### Naming the logical day

**Decided: a logical day is named for the calendar date it starts on.** A day with a 02:00 cutoff spans e.g. Tue 02:00 → Wed 02:00, and is called Tuesday.

This is what makes late-night work keep the right streak alive. The alternative — naming a day for the date it ends on — shifts every ordinary daytime session a day forward, which is the tell:

| Session | Cutoff 02:00, named by start (decided) | Named by end (rejected) |
|---|---|---|
| Tue 23:00 → Wed 01:00 | **Tuesday** | Wednesday |
| Wed 10:00 → Wed 11:00 | **Wednesday** | Thursday |

### One definition, one helper

The day logic is currently scattered and inconsistent: `timezone.localdate()` in `daily_goals.py`, `timezone.localtime(ts).date()` in `UserLogin`, and `timezone.now().date()` — a **UTC** date regardless of the player — in `progression/views.py:253`. New `progression/day_boundaries.py` owns:

- `logical_date_for(player, moment) -> date`
- `logical_day_bounds(player, day) -> (start, end)`
- `current_logical_date(player) -> date`

Every day-based query routes through it. **This is the actual deliverable of phase C** — the settings field is trivial by comparison.

## 3. Files likely to change

**Phase C — logical days**
- `users/models.py` (exists) — `day_start_time = TimeField(default=time(2, 0))` on `CustomUser`, next to the existing `timezone` field.
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

**Phase D — persisted session limits**
- `gameplay/models.py` (exists) — `limit_seconds` (positive int, null/0 = unbounded) and `limit_reason` on `ActivityTimer`. **Not** `duration`: `TimeRecord.duration` already means *elapsed* time, and the deleted `QuestTimer` used `duration` for the bound — the collision would be a silently wrong number, not a type error.
- `gameplay/migrations/00XX_*` (new) — the fields.
- `gameplay/serializers.py` (exists) — expose both, so the client stops reconstructing the limit from `is_premium`.
- `gameplay/views.py` (exists) — accept a limit on `set_activity`/`start`, clamped server-side to `GameSettings.free_timer_limit_seconds` for non-premium players rather than trusting the client's clamp.
- `gameplay/tasks.py` (exists) — the sweep completes bounded sessions whose declared end has passed, and skips them in the pause path.
- `frontend/src/hooks/useActivityTimer.ts`, `context/GameContext.tsx`, `context/WebSocketContext.tsx` (exist) — read `limit_seconds` from the server payload instead of deriving it at both `loadFromServer` call sites.

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

**g. Default cutoff 02:00, per-user override.** Late enough to keep most evening-into-night work on the day it belongs to, without pushing genuinely early-morning sessions onto the previous day. Per-user, so night owls can push it later and early risers can set strict midnight.

**h. Resume is offered only while the session's own logical day is current.** Past that, the paused card offers Submit or Discard. This is what stops a session started Tuesday and resumed three weeks later from crediting three weeks-old work to Tuesday — the distortion is in *resuming*, not in attributing time already banked, so attribution never needs a horizon. It also reads correctly: you don't resume yesterday's session, you finish it.

**i. A janitor completes paused sessions older than ~7 days**, crediting their original `logical_date`. `ActivityTimer` is `OneToOne` with `Player` and `set_activity` will 409 against a paused timer holding banked time, so an unresolved session hard-blocks starting a new one — the janitor is the safety valve if the UI ever regresses. Completing rather than discarding also softens (d): a player who never returns has their XP *delayed by up to a week*, not lost.

**j. A manual Pause button is deferred, but not designed out.** The state and endpoints already exist, and once Resume is in the UI a Pause button is one step away — but this plan is about interrupted sessions, not deliberate ones. Keep the paused card's Resume/Submit/Discard wording generic rather than "we interrupted you", so adding it later is a button rather than a rewrite. The resume horizon in (h) works unchanged for a manual pause.

**k. Login streaks move to logical dates too.** Not optional: `get_daily_goals_state` already queries `UserLogin` with `timestamp__date`, so once `today` is a logical date that comparison is logical-vs-calendar and the "logged in today" goal silently breaks for anyone active before the cutoff. Once that query moves, leaving the standalone streak on calendar dates would let the badge and the streak disagree about the same day. Logins are the easier half: they are only created in `users/signals.py` and `api/serializers.py`, both HTTP paths where the middleware has already activated the user's timezone.

**l. `DailyGoalAward.date` changes meaning without a migration.** Logical date equals calendar date outside the cutoff window, so at 02:00 only players active between midnight and 02:00 on changeover day can see a discontinuity, and `unique_daily_goal_award_player_date` bounds it to one extra award. A backfill would cost more scrutiny than the outcome is worth. Deploy the changeover at a low-traffic hour.

**m. A declared duration is the answer to "keep running while I'm away" — not a pause/continue setting.** An unbounded "never stop" toggle is an XP hole: opt in, close the laptop, accrue for days. A declared duration is bounded *by construction* — the server knows the end before the disconnect happens, so there is nothing to guess and nothing to cap after the fact. It is also a feature that was going to be built anyway (set a limit, count up or down to it), so the disconnect question is answered as a side-effect rather than by a setting that exists only to serve it.

Consequences:
- **Crediting forks, principledly.** An unbounded session credits to the last confirmed heartbeat (`truncate_to_last_heartbeat`). A bounded one credits `min(elapsed, limit_seconds)` — you declared 45 minutes, you get at most 45 minutes. That fork is the reason the limit has to be server-side; it cannot be derived from a heartbeat.
- **It closes an existing hole.** `GameSettings.free_timer_limit_seconds` is enforced only in `tickMain`, in the browser. Under phase B a free player who closes the tab has their session *paused* rather than capped, so the free-tier limit stops being enforced at all. Persisting the limit fixes that.
- **It fixes a live bug.** Both `loadFromServer` call sites rebuild the limit as `is_premium ? null : freeTimerLimitSeconds`, so a premium player's custom 45-minute duration silently vanishes on any reload or websocket reconciliation, and a free player's shorter chosen duration resets to the full 30 minutes. The client already collects a duration (`useSupportFlow`'s `durationSeconds`) and already has the whole `limitSeconds` / `limitReason` / `limitReached` / `autoStopCompletion` pipeline — the missing half is entirely server-side.
- **Scope.** This plan owns *persisting the limit and having the server honour it*. The feature proper — count-up vs count-down display, presets, editing mid-session — is separate work that builds on it.

**n. `limit_seconds` is a hard stop in both display modes.** Confirmed: counting up to a target stops at the target just as counting down does. So count-up vs count-down is purely a presentation choice over a single field — no second `target_seconds`, no soft-target semantics, and no way for the two to drift apart. This is also what the free tier needs and what `tickMain` already does.

It keeps phase D's surface minimal: the server needs `limit_seconds` and nothing else. The display preference never has to reach the backend or the timer payload, so it stays a client concern belonging to the feature work rather than to this plan.

## 5. Edge cases

- **A session spanning the cutoff itself** (01:00 → 03:00 at a 02:00 cutoff). Attributed wholly to the day it started — no split, per section 2.
- **A cutoff or timezone change** with sessions already recorded. Storing `logical_date` means history is untouched; only future sessions use the new setting. Worth saying so in the settings UI, since "my streak didn't change" could otherwise read as a bug.
- **A session started before a cutoff change and completed after.** `logical_date` is stamped at start, so it keeps the old day. Correct and unambiguous.
- **Retroactive goal completion.** A Tuesday session submitted Wednesday can complete Tuesday's goals after Tuesday ended. Bounded to that session's own logical day. `DailyGoalAward`'s unique constraint already makes it idempotent, but the badge query and the award path must agree on *which* day is being awarded.
- **A paused session whose logical day has ended.** Resume is withdrawn (h) and only Submit/Discard remain, so a session can never mix time from two logical days under one date. The paused card has to explain *why* Resume is gone, or its absence reads as a bug.
- **A paused session resolved days later** still credits its original `logical_date`, including that day's goals — retroactively, after the day has ended. Intended: the work happened when it happened. Bounded by the janitor (i) at ~7 days.
- **Manual/offline activities** (`Origin.MANUAL`) carry a user-supplied `started_at`; stamp `logical_date` from it, not from `now()`.
- **A bounded session that ran to its declared end while the player was away** is completed, not paused, so the resume horizon (h) never applies to it. The two auto paths must agree on which sessions are bounded, or a bounded session gets paused and then completed twice.
- **A bounded session paused and resumed** still counts banked time toward its own limit, server-side as well as in `tickMain` — otherwise pause/resume becomes a way to extend a free-tier session indefinitely.
- **A limit arriving from the client** is a claim, not a fact: clamp to `free_timer_limit_seconds` server-side for non-premium players rather than trusting the client's clamp.
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
- Resume is offered while the session's logical day is current and withdrawn once it has passed; Submit still credits the original day.
- The janitor completes paused sessions past the horizon against their original `logical_date`, and leaves newer ones alone.
- Backfill migration produces the expected dates for representative existing rows.

**Persisted limits**
- A custom duration survives a reload and a websocket reconciliation (the current bug: it is rebuilt from `is_premium` and lost).
- A bounded session whose end passes while disconnected is completed at its declared end, crediting `min(elapsed, limit_seconds)` — not credited to the last heartbeat, and not paused.
- An unbounded session in the same circumstances is paused, not completed.
- A non-premium player's oversized limit is clamped server-side, not just in the client.
- Pause/resume cycles do not let a bounded session exceed its limit.

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

- **Naming the new field `duration`.** `TimeRecord.duration` means *elapsed*; the deleted `QuestTimer.duration` meant *the bound*. Reusing the name gives two fields with opposite meanings one attribute lookup apart, and the failure mode is a plausible-looking wrong number rather than an error. `loadFromServer` already reads a stray `duration` off the timer payload, left over from that era — clean it up rather than build on it.
- **Shipping phase B's backend before its frontend** — turns a recoverable interruption into silent data loss via `set_activity`. The phase order and the server-side 409 both exist for this; they must not be collapsed into one PR.
- **Treating `isActive` as one concept.** `useActivityInput` derives `isActive = status === "active"` and uses it for two different questions ("is a session in progress" vs "is it ticking"). The likeliest frontend bug is a missed call site.
- **Leaving one day computation on the old convention.** A single stray `localdate()` or `completed_at__date` and the badge disagrees with the streak. Grep for all of them; there are at least four today, and one is already wrong (UTC).
- **Backfill drift.** Getting the backfill subtly wrong silently rewrites history for every existing player. Dry-run it against production-shaped data and eyeball a sample of boundary-crossing rows.
- **DST.** Adding a fixed offset instead of doing the arithmetic in the player's zone gives an off-by-one-hour boundary twice a year. Use `ZoneInfo` and localised datetimes throughout; never `timedelta`-shift a UTC instant to fake a local day.
- **Forgetting the XP-modifier pairing** — calling `timer.pause()` directly instead of `pause_server_timers()` leaves the online boost running against a paused session.
- **Losing `truncate_to_last_heartbeat`** in the pause rewrite — `Timer.pause()` → `apply_elapsed()` credits to `now()`, silently banking the whole detection window as worked time.
- **Missing the beat-schedule cleanup**, leaving a `PeriodicTask` row pointing at a renamed task: the sweep stops running, quietly.

## 8. Open questions

Day naming, the cutoff value, the resume horizon, the abandoned-session janitor, login streaks, the manual Pause button, the `DailyGoalAward` discontinuity and the shape of "keep running while away" are all resolved — see section 2 and 4g-4n. One remains:

1. **Should the disconnect grace period survive phase B?** Its purpose was delaying an irreversible action; pausing is cheap and reversible, and phase D removes the question entirely for bounded sessions. Pausing immediately would delete the countdown task, its cache key, the revoke in `connect()`, the supersede guard and the `still_connected` guard — replaced by a `paused_by` flag with bounded auto-resume on reconnect, which undoes a brief blip without presuming on a long absence. Larger refactor than shortening the grace period, and the same flag is what a manual Pause button (j) would need, so there is a case for doing it while that code is already open.

Two things are noted rather than asked, since they are scoping calls rather than design ones:

- The bounded-timer **feature** (count-up vs count-down display, duration presets, editing a limit mid-session) is separate work. This plan owns only the persistence and server enforcement it rests on.
- Phase D's fields are small, but they change what `set_activity` and `start` accept. Worth confirming no other client depends on the current shapes before the serializer changes.
