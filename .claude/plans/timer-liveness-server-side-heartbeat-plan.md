# Timer liveness — derive presence from the websocket, not from page JS

Follow-up to PR #804, which widened the thresholds that were auto-completing live timers. This plan removes the underlying fragility rather than tuning around it.

## 1. High-level strategy

`Player.last_seen` is the signal `auto_complete_timers_for_stale_players` and `reconcile_stale_online_players` judge a player on, and it is fed by a `setInterval` in the player's browser tab. Page timers are throttled when a tab is backgrounded, frozen when it is discarded, and stopped entirely when the device sleeps — so `last_seen` reports "this tab's JS is running promptly", not "this player is connected".

A reliable signal already exists and is already running in production: Daphne sends a websocket protocol-level ping every 20s (`--ping-interval`, default 20) and closes any connection that doesn't pong within 30s (`--ping-timeout`, default 30; wired to autobahn's `autoPingTimeout` in `daphne/server.py`). Protocol pings are answered by the browser's network stack, not by page JS, so they keep working through throttling and freezing. An open socket is therefore trustworthy evidence of presence in a way a JS interval never is.

Plan: move the stamping of `last_seen` from the browser into `TimerConsumer` — a small async loop that stamps for as long as the socket is open — then delete the client heartbeat and re-tune the sweep threshold to reflect what it now measures.

No new models, services, endpoints, or migrations: this reuses `last_seen`, `record_heartbeat()`, and both existing sweeps unchanged in structure.

## 2. Files likely to change

**Backend**
- `gameplay/consumers.py` (exists) — start a periodic `last_seen` stamp task in `connect()`, cancel and await it in `disconnect()`. `record_heartbeat()` already exists and is already `database_sync_to_async`; reuse it as the loop body. Keep the `ping` branch in `receive_json` (see 4d).
- `gameplay/tasks.py` (exists) — re-tune `STALE_TIMER_THRESHOLD` and rewrite its comment: it now measures "no ASGI process is holding a socket for this player", not "the player's tab missed some pings".
- `users/tasks.py` (exists) — same for `STALE_CONNECTION_THRESHOLD`'s comment; the value can likely stay.
- `gameplay/tests/test_stale_connection_sweep.py` (exists) — the browser-throttling tests added in PR #804 no longer describe the mechanism; reframe them.
- `gameplay/tests/test_consumer_heartbeat.py` (new) — the consumer's disconnect behaviour lives in `test_disconnect_grace.py`, but the heartbeat task is a separate concern and that file is already long.

**Deployment config** (all four Daphne launch points — the design now depends on the keepalive, so it should be explicit rather than inherited from defaults)
- `render.yaml`, `render-staging.yaml`, `compose.yaml`, `Dockerfile` (all exist) — add `--ping-interval 20 --ping-timeout 30` to the `daphne` command.

**Frontend**
- `frontend/src/hooks/useWebSocketHeartbeat.ts` + `.test.ts` (exist, added in #804) — delete.
- `frontend/src/context/WebSocketContext.tsx` (exists) — drop the `useWebSocketHeartbeat` call.
- `frontend/src/websockets/handleGlobalWebSocketEvent.ts` (exists) — the `pong` case becomes dead; remove it and the `ping`/`pong` message types in `frontend/src/types/timers.ts` once the server-side `ping` handler is retired (see 4d).

## 3. Implementation plan

Four commits, each safe to deploy on its own. Order matters: presence gets *more* reliable at every step, and the client heartbeat is only removed once the server one is proven.

1. **Make the Daphne keepalive explicit.** Config only, no behaviour change (the values match the defaults already in force). Establishes the invariant the rest of the plan rests on, and makes it visible to anyone editing those commands later.
2. **Add the server-side heartbeat.** `TimerConsumer` stamps `last_seen` on connect and every ~60s while the socket is open. Both client and server now stamp; `last_seen` can only get fresher, so no timer can start dying earlier than it does today. Deploy and confirm on staging that `last_seen` stays fresh for a tab left backgrounded for 15+ minutes.
3. **Remove the client heartbeat.** Delete the hook and its usage. Presence is now entirely server-derived. Leave the consumer's `ping` handler in place — browsers still running the previous bundle will keep sending pings, and they should not get errors.
4. **Re-tune `STALE_TIMER_THRESHOLD`.** Last, deliberately: tightening the threshold is the only step that can shorten a live session, and it should only happen once step 2 has been observed working. With a 60s server stamp, ~4 minutes tolerates three consecutive missed stamps.

A later fifth commit can retire the `ping`/`pong` plumbing on both sides, once no meaningful number of clients are running a pre-step-3 bundle.

## 4. Design decisions

**a. Periodic stamp from the consumer, vs. reacting to Daphne's pongs.**
Reacting to pongs would be the most direct expression of "the socket is alive" — but Daphne handles ping/pong entirely inside `ws_protocol.py` and surfaces nothing to the ASGI application, so a consumer cannot observe them without patching Daphne. The periodic stamp gets the same guarantee indirectly: the loop only runs while the consumer is alive, and Daphne guarantees the consumer doesn't outlive a client that has stopped answering pings. Chosen for being ordinary code with no dependency on Daphne internals.

**b. Keep presence in `Player.last_seen`, vs. a Redis key with a TTL.**
A TTL key is arguably the more natural fit — presence is ephemeral, and expiry would replace the sweep's threshold arithmetic. But both sweeps are currently single indexed queries joining on `last_seen`, and moving to Redis would turn `auto_complete_timers_for_stale_players` into a per-player cache lookup and split presence across two stores (the admin's `last_seen` column, `Player.online_count()`, and the online badge all read the DB today). Reusing the existing column keeps this to a change of *who writes it*, which is the actual bug. Revisit if per-connection writes become a load concern (see 7).

**c. Stamp interval ~60s against a ~4 minute threshold.**
The stamp is a single indexed `UPDATE` by PK with no reads, so the cost is one small write per connected player per minute. It doesn't need to be fast — it isn't detecting anything, just proving the process is alive — and the ratio should stay generous enough to absorb a slow worker or a brief DB blip. Pin the relationship in a test rather than leaving the two constants to drift, the way #804 did with the heartbeat interval.

**d. Keep the consumer's `ping` handler through the rollout.**
Browsers hold onto a loaded bundle indefinitely. Removing the server handler at the same time as the client sender would make every still-open old tab log `Unknown type received: ping`. It costs one branch to leave it.

**e. Not changing: whether auto-completing is the right response at all.**
Out of scope here, and worth deciding separately — see 8. This plan makes the "is the player gone?" answer trustworthy; it does not revisit what should happen when the answer is yes.

## 5. Edge cases

- **Task cancellation.** `disconnect()` must cancel *and await* the task. Cancelling without awaiting leaves a window where an in-flight stamp lands after `unregister_connection()`, refreshing `last_seen` for a player who has just left — which would suppress the sweep for a full threshold window.
- **Transient DB errors in the loop.** A failed stamp must be caught and the loop continued. An unhandled exception kills the task silently, the socket stays open, and the player is swept mid-session — the exact bug this plan exists to remove, with a rarer trigger.
- **Zombie sockets.** The design's one hard dependency: if `--ping-interval` is ever set to 0 or the keepalive is otherwise disabled, a client that vanishes without a TCP close leaves the socket (and the stamping loop) alive indefinitely, and its timer runs forever. Hence commit 1, plus a comment in the consumer naming the dependency.
- **Multiple tabs.** N connections stamp the same row redundantly. Harmless — same value, no read-modify-write, no lock needed.
- **Process death (OOM, deploy restart).** Stamps stop with no `disconnect()`. This is precisely the case the sweep is the backstop for, and it now works on a signal that means what the sweep assumes.
- **Consumer tests that build `TimerConsumer` by hand.** `test_disconnect_grace.py` constructs consumers directly rather than through `connect()`; `disconnect()` must tolerate the heartbeat attribute being absent.
- **Rollout ordering.** Steps 2 and 3 are independent deploys of two services. Between them both sides stamp; if step 3's frontend deploy somehow precedes step 2's backend deploy, presence falls back to today's behaviour rather than breaking.
- **No migration, no API change, no serializer change.** `last_seen` already exists and is not exposed to clients.

## 6. Tests

**New — `gameplay/tests/test_consumer_heartbeat.py`**
- Connecting starts the task and stamps `last_seen`.
- The loop stamps repeatedly while connected (drive it with a patched interval and a short `asyncio.sleep`, rather than waiting on wall-clock time).
- `disconnect()` cancels the task, and no stamp lands afterwards — assert `last_seen` is unchanged after the disconnect returns.
- A stamp raising a DB error doesn't kill the loop: the next tick still stamps.
- Guard test: the stamp interval is comfortably below `STALE_TIMER_THRESHOLD`, so the two constants can't drift apart.

**Modify — `gameplay/tests/test_stale_connection_sweep.py`**
- `StaleTimerThresholdTests` (added in #804) reasons about missed *browser* heartbeats; re-express it against the server stamp interval.
- `test_backgrounded_tab_with_a_throttled_heartbeat_is_not_swept` no longer describes a real mechanism — a backgrounded tab's heartbeat is no longer throttled. Replace with the case that still matters: a player whose process died mid-session is swept, and one whose connection is alive is not.

**Modify — `gameplay/tests/test_disconnect_grace.py`**
- Existing tests should pass untouched; confirm the hand-built consumers still disconnect cleanly with the heartbeat attribute unset.

**Delete**
- `frontend/src/hooks/useWebSocketHeartbeat.test.ts`, with the hook.

## 7. Risks

- **Leaking the task** — the highest-consequence mistake, and silent. A consumer that fails to cancel its loop keeps a departed player looking present forever, so their timer is never swept. Worse than the bug being fixed, and invisible without a test that asserts no stamp lands after disconnect.
- **Cancelling without awaiting** — the same failure in miniature, and easy to miss in review because the cancel line is present.
- **Over-broad exception handling** — `except Exception: pass` inside the loop turns a persistent DB failure into silence. Log it.
- **Removing the client heartbeat before the server one is deployed** — leaves a gap with no presence signal at all, during which every running timer is swept at the threshold. Steps 2 and 3 must not be combined into one PR.
- **Setting the stamp interval too close to the threshold** — reintroduces #804's "one missed beat kills the session" with a different actor. The guard test exists for this.
- **Assuming the keepalive without checking** — anyone adding a Daphne flag later can disable pings without realising the sweep depends on them.
- **Per-connection write volume at scale** — one write per player per minute is fine now and worth watching; it is the reason 4b is written as revisitable rather than settled.

## 8. Open questions

1. **Should a sleeping device end a session?** With presence tied to the socket, a locked phone or closed laptop ends the timer after the grace period. For "start a timer, go for a run", that is the wrong answer, and no amount of liveness engineering fixes it — it needs an explicit affordance (a declared duration, or "keep running while I'm away"). Worth deciding before this ships, because it determines whether socket liveness is the right signal or merely a better one.
2. **Is auto-completing the right response to an ended session at all?** Pausing the timer and letting the player resolve it on return loses no work and needs no XP guesswork. Auto-complete exists to stop runaway XP accrual; a cap would too, less destructively.
3. **Concrete values** for the stamp interval and `STALE_TIMER_THRESHOLD` — the plan assumes ~60s and ~4 minutes.
4. **Does Render's proxy impose its own websocket idle timeout?** Daphne's 20s pings should keep connections non-idle regardless, but it's worth confirming rather than assuming, since a proxy-side disconnect looks identical to a client-side one.
5. **How long to keep the `ping`/`pong` plumbing** before the step-5 cleanup — depends on how aggressively cached bundles turn over.
