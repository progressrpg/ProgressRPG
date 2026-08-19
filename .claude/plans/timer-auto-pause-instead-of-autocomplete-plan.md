# Auto-pause an interrupted timer instead of auto-completing it

Open question 2 from `timer-liveness-server-side-heartbeat-plan.md`, promoted to its own plan.

## What already exists

Worth stating up front, because it shapes the whole plan:

- `paused` is already a `Timer.STATUS_CHOICES` value, `Timer.pause()` banks elapsed time, and `Timer.start()` resumes correctly from paused (keeps `elapsed_time`, sets a fresh `start_time`; `get_elapsed_time()` sums them).
- `/activity_timers/pause/` and `/activity_timers/start/` already exist on `BaseTimerViewSet`, and both broadcast.
- `pause_server_timers()` in `gameplay/utils.py` pairs the pause with `set_activity_active_modifiers(is_active=False)` — the online-boost side-effect that a bare `timer.pause()` misses.
- `useActivityTimer.loadFromServer` already handles a paused snapshot correctly: banks `elapsed_time` into `pausedTimeRef`, starts no interval. `tickMain` already computes `pausedTimeRef.current + secondsPassed`, which *is* resume semantics.
- `TimerStatus` in the TS enums already includes `"paused"`.

So the mechanics are largely built. Two things are missing, and one is actively dangerous:

- **No UI represents it.** `useActivityInput` derives `isActive = status === "active"`, so a paused timer reads as *no timer at all* — and starting anything then calls `set_activity` → `new_activity()`, which resets `elapsed_time` to 0. **Pausing without the UI work would destroy the player's time rather than bank it**, which is strictly worse than auto-completing.
- **Its one production trigger is broken.** `server_management/management/commands/pause_timers.py` filters `status="Active"`; the stored value is `"active"`, so maintenance mode has been pausing zero timers. The paused state has effectively never been exercised in production.

## 1. High-level strategy

Auto-completing is a destructive answer to an uncertain question. The server guesses the player is gone, and if it guesses wrong it force-submits a session the player was in the middle of — irreversibly, since completion awards XP, writes a `PlayerActivity`, and fires daily-goal and streak logic.

Pausing answers the same question non-destructively: bank the elapsed time, stop accruing, and let the player decide on return. It still solves what auto-complete was for — a dead connection can no longer accrue XP forever — but a wrong guess now costs a resume click instead of a lost session.

The work is mostly frontend. Backend-side this is a substitution: `timer.complete(...)` → `pause_server_timers(timer)` in the two auto paths, keeping `truncate_to_last_heartbeat()` from #804 so the banked time reflects the last confirmed heartbeat rather than the moment the sweep noticed.

Note the interaction with the liveness plan: **this lowers the stakes of that one considerably.** Once a false "player is gone" verdict costs a pause, the exact threshold matters much less. These are independent and either can ship first, but if both are wanted, this one buys more safety per unit of risk.

## 2. Files likely to change

**Frontend** (the bulk — paused must become a first-class state)
- `frontend/src/components/ActivityInput/useActivityInput.ts` (exists) — `isActive` currently answers two different questions ("is a session in progress" and "is it ticking"). Split: keep `isActive` for ticking, add `isPaused`/`hasSession`. Audit all ~10 uses (`isUnlabelled`, `inputValue`, `handleToggle`, `handleUnifiedSelect`, `handleUnifiedSubmit`, the auto-stop warning) for which meaning each wants. Add resume/discard handlers.
- `frontend/src/components/UnifiedTimerHome/UnifiedTimerHome.tsx` (exists) — render the paused state: banked elapsed, activity name, and Resume / Submit / Discard. `statusMessage` needs a third branch (it currently reads "Timer stopped" for paused, which is a lie — the time is still banked).
- `frontend/src/hooks/useActivityTimer.ts` (exists) — add `resume()`: POST `/activity_timers/start/`, then set status active with `pausedTimeRef` at the banked elapsed and `startTimeRef` at now. Small, because `tickMain` already does the arithmetic.
- `frontend/src/types/timers.ts` (exists) — add `resume` to `ActivityTimerReturn`.

**Backend**
- `gameplay/tasks.py` (exists) — both auto paths pause instead of complete. Rename `auto_complete_timer_on_disconnect` → `auto_pause_timer_on_disconnect` and the sweep likewise; keep `truncate_to_last_heartbeat` and the `still_connected` guard from #804 unchanged.
- `gameplay/consumers.py` (exists) — the disconnect branch names the renamed task; `DISCONNECT_TASK_CACHE_KEY` and the grace constant keep working as-is. The existing "pause non-active timers immediately" branch can now fold into one path.
- `gameplay/views.py` (exists) — guard `set_activity` against a paused timer holding banked time (see 4c).
- `server_management/management/commands/pause_timers.py` (exists) — fix the `"Active"` filter. Not drive-by any more: maintenance pausing is about to become a state players actually see.
- `progress_rpg/celery.py` (exists) — rename the beat entry to match the renamed task. Note the `locations/migrations/0002_*` comment: `django_celery_beat`'s DatabaseScheduler does not remove stale `PeriodicTask` rows, so the old entry needs an explicit cleanup migration or a manual delete.
- `gameplay/tests/test_disconnect_grace.py`, `gameplay/tests/test_stale_connection_sweep.py` (exist) — assert pausing, not completing.
- `gameplay/tests/test_views.py` (exists) — the `set_activity` guard.

No model changes and no migrations: `paused` and every endpoint this needs already exist.

## 3. Implementation plan

Frontend first, deliberately. Nothing produces a paused timer today (the maintenance command is broken), so the UI work is dormant until the backend switches — which means each step is independently safe, and the dangerous ordering (backend pauses while the UI still reads paused as "no timer") never occurs.

1. **Make paused a first-class client state.** `resume()` in `useActivityTimer`, the `isActive`/`isPaused` split in `useActivityInput`, the paused UI in `UnifiedTimerHome`. Testable immediately by seeding a paused timer server-side; ships as a no-op.
2. **Guard `set_activity`, fix the maintenance command.** Backend-only, no behaviour change for anyone not already paused. After this the whole pause/resume/discard loop works end to end and can be exercised via maintenance mode or the admin action.
3. **Disconnect grace pauses instead of completing.** The smaller blast radius of the two auto paths, and the one with a 120s window, so mistakes surface fast.
4. **Stale sweep pauses instead of completing.** Same substitution, plus the beat-schedule rename and its `PeriodicTask` cleanup.
5. **(Optional) Janitor for abandoned paused timers.** See 4e — worth its own decision, not a prerequisite.

## 4. Design decisions

**a. Paused state shown inline, vs. a modal on return.**
A modal ("You have a paused session — resume or submit?") is more assertive and guarantees the player notices. But the timer UI has to represent paused anyway — a paused-but-invisible timer is what makes the current code dangerous — and once it is represented, a modal is a second way to say the same thing. Inline also handles the reload case gracefully: coming back to a paused session at your desk shouldn't be a dialog to dismiss. Chosen: inline, with the paused card visually distinct enough not to be mistaken for a running timer. Revisit if testing shows people miss it.

**b. Explicit resume, vs. auto-resume on reconnect.**
Auto-resume is tempting and technically lossless (elapsed is banked; resuming just continues). But it re-arms a timer without being asked — a player who closed their laptop at 5pm and opens it at 9am would find yesterday's "Write report" session running and accruing. The whole point is to stop the server deciding on the player's behalf; auto-resume swaps one presumption for another. Chosen: explicit.

**c. `set_activity` refuses when banked time exists, and Discard routes through `/reset/`.**
The silent-wipe path is the sharpest edge here, and the UI not offering it is not enough — a stale tab, a queued request, or a future caller can still hit `set_activity`. So the endpoint returns 409 when the timer is paused with `elapsed_time > 0`, and Discard calls the existing `/activity_timers/reset/` first. Reuses an endpoint that already does exactly this rather than adding a `discard=true` flag.
Alternative considered: have `set_activity` auto-complete the paused session before starting the new one. Rejected — it reintroduces exactly the surprise submission this plan removes.

**d. Reuse `pause_server_timers()`, not `timer.pause()`.**
The XP-modifier side-effect is the reason. A bare `timer.pause()` leaves `set_activity_active_modifiers` on, so the online boost keeps running against a paused session. `pause_server_timers` already pairs them and is plain sync code callable from a Celery task.

**e. Abandoned paused timers: leave them, initially.**
A player who never returns leaves a paused timer indefinitely. Auto-complete at least closed the books. Options: a slow janitor completing paused timers older than N days, or leaving them for the player. Leaving them is simpler and loses nothing — a paused timer costs one row and resolves itself whenever they next log in. Deferred to step 5 rather than assumed; see 8.

**f. Accepted trade-off: a player who never returns now gets no XP for work they did do.**
Auto-complete awarded it. This is the real cost of the change, and it is worth naming rather than burying: the plan trades certain-but-sometimes-wrong XP for correct-but-deferred XP. Given the reported failure mode was *live* sessions being force-submitted, that seems the right way round — but it is a product judgement, not a technical one.

## 5. Edge cases

- **`set_activity` on a paused timer** — the silent-wipe path; covered by 4c, and the single most important test in this plan.
- **The free-tier limit across a pause/resume.** `limitSeconds` is compared against total elapsed in `tickMain`, so a resumed session correctly counts banked time toward the cap. But `loadFromServer` resets `didAutoStopRef` and `limitReached` — check that a session resumed *past* its limit auto-stops immediately rather than running unbounded.
- **Resume racing the sweep.** The player clicks Resume as the sweep pauses the same timer. Both are single writes on one row and the outcome is one of two consistent states; the loser gets corrected by the resulting broadcast. No lock needed — worth stating explicitly rather than reaching for one.
- **Resume from a second tab.** `broadcast_activity_timer` already reconciles other sessions via `loadFromServer`. This path becomes more common once paused sessions are visible, so it needs a real test rather than an assumption.
- **`activity.started_at` across a long pause.** Set on first `start()` and not re-stamped on resume, so a session started at 09:00, paused, and resumed at 17:00 reports `started_at` 09:00 with ~20 minutes elapsed. Correct for XP; possibly odd in the activity timeline. Decide whether the timeline should read `started_at` or derive from elapsed.
- **Orphaned `PlayerActivity` rows.** `new_activity()` creates a row per call and overwrites the FK, so abandoned incomplete activities already accumulate today. The Discard path (`reset` then `set_activity`) inherits this; not made worse, but worth a look while in the area.
- **Beat-schedule rename.** `DatabaseScheduler` leaves the old `PeriodicTask` row in place, pointing at a task name that no longer exists. Needs an explicit cleanup, per the precedent in `locations/migrations/0002_disable_wander_tick_periodic_task.py`.
- **Deploy ordering.** Step 1 ships dormant; steps 3-4 only start producing paused timers after the UI understands them. A frontend rollback after step 3 would reintroduce the invisible-paused-timer hazard — which is the argument for the 4c guard being server-side.

## 6. Tests

**Backend**
- Disconnect grace: an active timer is paused, not completed; `elapsed_time` is banked to the last heartbeat; no XP is awarded and no `PlayerActivity` is completed; the `still_connected` guard still short-circuits.
- Stale sweep: same assertions; a paused timer is not swept again on the next tick (it is no longer `status="active"`, so this should hold for free — assert it, since it is the property that stops the sweep looping).
- Pause preserves the resume path: `pause()` then `start()` then `complete()` credits the sum of both segments, not just the second.
- `set_activity` returns 409 against a paused timer with banked time, and still works against `empty`/`waiting`.
- `pause_timers` management command actually pauses active timers (would have failed before the case fix).
- XP modifiers are deactivated on auto-pause and reactivated on resume.

**Frontend**
- `useActivityTimer`: `resume()` continues from banked elapsed rather than restarting at zero; `loadFromServer` with a paused snapshot shows banked time and does not tick.
- `useActivityInput`: a paused timer is not treated as "no timer" — starting a new activity from the paused state is blocked or routed through Discard.
- `UnifiedTimerHome`: the paused card renders elapsed + Resume/Submit/Discard; the status message distinguishes paused from stopped (a11y — this is what a screen-reader user has instead of the visual card).
- Free-tier limit: resuming a session already past its limit stops immediately.

## 7. Risks

- **Shipping the backend switch before the UI** — turns a recoverable interruption into silent data loss. The step order and the 4c server-side guard both exist for this; they should not be collapsed into one PR.
- **Treating `isActive` as one concept.** It currently answers two questions and every call site has to be re-read to decide which it meant. The likeliest bug in this plan is a missed call site where a paused timer starts behaving like a running one (or like nothing at all).
- **Forgetting the XP-modifier pairing** — calling `timer.pause()` directly leaves the online boost running against a paused session. Easy to do, since `pause()` is the obvious method.
- **Losing `truncate_to_last_heartbeat`** in the rewrite. `Timer.pause()` → `apply_elapsed()` credits up to `now()`, so dropping the truncation silently banks the entire detection window as worked time.
- **Missing the beat-schedule cleanup**, leaving a `PeriodicTask` row pointing at a renamed task — fails quietly in the worker log while the sweep stops running entirely.
- **Assuming paused is exercised today.** It is not (broken maintenance command), so anything "already working" in that state should be verified rather than trusted — including the `loadFromServer` paused branch this plan leans on.

## 8. Open questions

1. **Should very old paused timers eventually be closed out?** If so, on what horizon, and completed (awarding XP) or discarded? This is the mirror of 4f — a 3-week-old paused "Write report" is not a session anyone wants resumed, but silently binning it loses real work.
2. **Does an interrupted session still count toward streaks and daily goals?** Today auto-complete makes it count. Under this plan nothing counts until the player resolves it, which could break a streak for someone whose wi-fi dropped at 23:50. Worth checking against `check_and_award_daily_goals` and the login-streak logic.
3. **Should a manual pause be offered too?** The state and endpoints exist; exposing Resume in the UI puts a Pause button one step away, and it is arguably the feature players would ask for. Deliberately out of scope here — this plan is about interrupted sessions — but the UI should be built so that adding it later is not a rewrite.
4. **Should the disconnect grace period still exist?** Its purpose was delaying an irreversible action. Pausing is cheap and reversible, so pausing immediately on disconnect (and letting reconnect resume) may be simpler than keeping a revocable countdown task, its cache key, and its supersede guard.
5. **What does the character do while a timer is paused?** Activity timers drive character progression via the linked character's behaviour; whether a paused player's character idles, continues, or pauses too is a game-design question this plan does not touch.
