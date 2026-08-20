# Frontend Vitest Restructuring for Speed

## Context

Follow-up to the Tamagui-extraction fix (PR #789, merged into `npm run test`'s `unit` project), which cut `npm run test` from ~58s to ~43s by skipping Tamagui's build-time style compiler for tests. This plan covers further, code-level restructuring opportunities found while profiling the remaining ~43s, using Vitest's JSON reporter (`--reporter=json`) for per-file timings and controlled `maxWorkers`/flag experiments. All numbers below are measured in this sandbox (4 CPUs) and are relative, not absolute guarantees on other hardware.

Previously investigated and rejected (do not re-attempt without new evidence):
- `test.isolate: false` — causes 25-44 test failures (mock state leaks across the 38 files using `vi.mock()`). Unsafe.
- `pool: 'threads'` instead of default `forks` — no measured speed difference.
- **Splitting `Map.test.tsx` into 3 files (Opportunity 1 below) — implemented, measured, and reverted.** Built the split exactly as planned (shared `Map.testHelpers.tsx` + 3 test files) and ran a clean A/B on identical machine state: unsplit baseline ~42.7s/44.1s (two runs) vs. split ~44.6s/43.9s — no measurable difference, arguably a hair worse due to 2 extra files' worth of fixed per-file `environment`/`setup` overhead. Root cause: Vitest's default sequencer already schedules known-slow files first (confirmed via `vitest --help --sequence.shuffle.files`: disabling shuffle - the default - is what makes "long running tests start earlier"), so the single 17.3s `Map.test.tsx` was already getting dispatched onto its own worker at the start of the run, achieving close to the packing this split was meant to produce. This repo's CI also doesn't use `--shard`, so there was no secondary multi-machine-sharding win either. The split code was fully implemented and verified passing (44/44 tests, `tsc --noEmit` clean) before being reverted for not paying for itself - available in git history on `claude/pr-702-review-wii8hq` if this needs revisiting under different scheduling conditions.

---

## 1. High-level strategy

Originally three independent, separately-landable changes; the first (splitting `Map.test.tsx`) was implemented and measured but reverted - see Context above. Remaining:

1. ~~Split `Map.test.tsx`~~ — implemented, measured (no wall-clock benefit; Vitest's scheduler already handles this), reverted. Not part of the implementation.
2. **Centralize a `pointerEventsCheck: 0` userEvent helper** — **implemented.** Added `frontend/src/testUtils/setupUser.ts`; migrated all 35 files / ~150 call sites (audited first: no test in the codebase relies on the strict check itself - every `toBeDisabled()`/pointer-events reference was either a static assertion or clicked a *different* element that caused disabling, never a click on the disabled element expecting it to be blocked). Full suite: same 561 passed / 1 pre-existing unrelated failure before and after, `tsc --noEmit` and lint clean. Wall-clock effect on the full suite is modest (~42-44s baseline → ~42s after, within run-to-run noise) since `Map.test.tsx`'s isolated ~18% improvement doesn't fully translate 1:1 once it's running concurrently with 69 other files - `user` (CPU) time dropped more consistently (~2m1-2m5s → ~1m59-2m0s), which matters more for CI compute cost than wall-clock alone.
3. **Flag, but do not yet implement**, reducing repeated `TamaguiProvider` mount cost in Tamagui-touching test files (`ProgressBar.test.tsx`, `Map.test.tsx`) — real (~150-250ms/test overhead measured) but requires trading off RTL's automatic per-test `cleanup()`/isolation, which needs more careful design than this pass affords. Proposed as a follow-up spike, not part of this plan's implementation.

Not proposed: reducing worker count assumptions, coverage/`test:ui` changes, or touching the `storybook` project (couldn't be verified in this sandbox — pre-existing Playwright binary mismatch, unrelated to test structure).

---

## 2. Files likely to change

| File | Change | Exists? |
|---|---|---|
| `frontend/src/components/Map/Map.test.tsx` | Split into 2-3 files; shared setup extracted | Yes (modified + reduced) |
| `frontend/src/components/Map/Map.test-helpers.tsx` (or similar, exact name TBD at implementation) | New: `FakeMap`/`FakeMarker`/`FakeGeoJSONSource` classes, `renderMap`, `currentMap`, `villageSourceFeatures`, `characterMarkers`, `positionAlongPathForTest`, shared fixtures | New |
| `frontend/src/components/Map/Map.entityDetailCard.test.tsx` | New: the `PopulationCentreMap entity detail card` describe block (currently lines ~1106-1399) | New |
| `frontend/src/components/Map/Map.pathInterpolation.test.tsx` | New: the `PopulationCentreMap path-aware interpolation (#615)` describe block (currently lines ~1400-end) | New |
| `frontend/src/testUtils/setupUser.ts` | New: shared `setupUser()` wrapping `userEvent.setup({ pointerEventsCheck: 0, ...overrides })` | New |
| ~34 `*.test.tsx` files currently calling `userEvent.setup()` | Swap to the shared helper, opportunistically or in one mechanical pass | Existing (modified) |

No production (non-test) source files change.

---

## 3. Implementation plan

**Step 1 — `Map.test.tsx` split (own PR)**
1. Extract the shared header (imports, both `vi.mock()` calls, `Fake*` classes, helper functions, `renderMap`, fixture builders currently at lines 1-314) into a new non-test helper module.
2. Keep `vi.mock('maplibre-gl', ...)` and `vi.mock('../../api/map', ...)` as short (1-line-ish) calls repeated in each of the 3 split test files — `vi.mock()` must be hoisted per-file by Vitest's transform, so the *factories* can be imported from the shared module, but the `vi.mock()` call sites themselves stay in each test file. This is standard Vitest practice, not a new pattern for this codebase.
3. Move the `PopulationCentreMap entity detail card` describe block to `Map.entityDetailCard.test.tsx`.
4. Move the `PopulationCentreMap path-aware interpolation (#615)` describe block (has its own `beforeEach` using fake timers) to `Map.pathInterpolation.test.tsx`.
5. Leave the main `PopulationCentreMap` describe block in `Map.test.tsx`.
6. Run all three files individually and together; compare total wall-clock and per-file timings against the current baseline (17.3s / 44 tests in one file) to confirm the parallelism benefit materializes, since Vitest's actual worker scheduling (not just file count) determines the real gain.

**Step 2 — shared `userEvent` helper (own PR, independent of Step 1)**
1. Add `frontend/src/testUtils/setupUser.ts` exporting a `setupUser(options?)` that defaults to `pointerEventsCheck: 0`, matching the `mockAuthContextValue`/`mockGameContextValue` convention already in `src/testUtils/`.
2. Migrate `Map.test.tsx` (and its post-split siblings) to it first, since that's the measured, verified win.
3. Migrate the remaining 33 files opportunistically — either as one mechanical follow-up PR (search-and-replace `userEvent.setup()` → `setupUser()`, drop the import), or file-by-file as they're next touched. Recommend the mechanical pass since the change is uniform and low-risk (see Design Decisions).

**Step 3 — TamaguiProvider mount-cost spike (not implemented here)**
- Time-box a spike to check whether sharing one `render()` + `rerender()` per file (instead of per test) for `ProgressBar.test.tsx` is safe and how much it saves, before committing to changing the pattern more broadly. Out of scope for this plan's implementation.

---

## 4. Design decisions

**Split boundary: existing `describe` blocks, not test count.**
- Alternative: split by roughly-equal test count (e.g., ~15 tests/file) regardless of topic.
- Why existing boundaries: they're already coherent behavioral groupings (main map behavior / detail-card interactions / path interpolation, the last of which has its own `beforeEach`/fake-timer setup that's already isolated). Splitting along them keeps each file's `beforeEach` and describe-local intent legible, and follows how the codebase already organizes test structure elsewhere. Splitting by count alone would need to still separate the fake-timer describe block anyway to avoid cross-contaminating other tests' timer setup, so it doesn't actually save work.

**Shared helpers as a non-test module, `vi.mock()` repeated per file.**
- Alternative: put `vi.mock('maplibre-gl', ...)` itself inside the shared module and have each test file just import it for side effects.
- Why not: Vitest hoists `vi.mock()` calls via static analysis of the file that calls them; moving the call into an imported module is a known footgun (mock hoisting order becomes import-order-dependent and fragile). Keeping the 1-line `vi.mock()` call in each file (referencing a shared factory) is the documented-safe pattern and only costs 3 near-identical lines total across the split files.

**Centralized `setupUser()` helper vs. per-call-site edits.**
- Alternative: mechanically add `{ pointerEventsCheck: 0 }` to all 149 call sites directly.
- Why a helper: matches the existing `src/testUtils/` convention (shared mock/setup helpers rather than duplicated inline config), and gives one place to revisit if a future test genuinely needs the strict check (see Edge Cases) rather than 149 places to search.

**Not touching `isolate` or `pool` again.**
- Already measured and rejected in prior investigation (see Context). Restated here only so this plan doesn't get re-litigated against them.

---

## 5. Edge cases

- **Tests that intentionally rely on the pointer-events check.** A test asserting that clicking a `pointer-events: none`/disabled element does *not* register a click could behave differently with the check disabled (userEvent would no longer throw/skip — it may now dispatch the event and the assertion might pass for the wrong reason, or fail differently). Audit call sites for this pattern specifically before the mechanical migration in Step 2, not after — grep for tests near `disabled`, `pointer-events`, or `toBeDisabled` assertions and leave those on the strict default.
- **Split-file cross-contamination.** The `path-aware interpolation` describe block uses its own `beforeEach` (fake timers) at line 1401 that must not leak into the other two files once split — since each becomes its own file, Vitest's default `isolate: true` already guarantees this is a non-issue (separate module registries), but worth an explicit note since it's exactly the isolation guarantee the earlier `isolate: false` experiment showed we depend on.
- **`FakeMap.instances`/`FakeMarker.instances` static arrays.** Currently reset in a file-level `beforeEach`. After the split, each file gets its own module instance of the shared helper (since ESM modules aren't shared state across separate test files/workers), so this remains file-scoped correctly — no change needed, but worth confirming empirically during implementation (Step 1.6) rather than assuming.
- **Import-order sensitivity.** `Map.test.tsx` currently does `const { default: PopulationCentreMap } = await import('./Map')` *after* both `vi.mock()` calls specifically so the mocks apply. Each split file must preserve this ordering independently — a straight copy-paste of the header per file (rather than a shared "run this setup" function) makes this easiest to get right and audit.

---

## 6. Tests

- No behavioral test changes — this is a pure restructuring of *where* existing assertions live and *how* `userEvent` is configured, not what's asserted.
- New tests: none needed for the restructuring itself.
- Existing tests to modify: the ~44 tests currently in `Map.test.tsx` move file (no content change) as part of Step 1; the `userEvent.setup()` call sites are swapped for `setupUser()` in Step 2.
- Verification for each step: full `npm run test` pass/fail count must stay identical (currently 561 passing / 1 pre-existing unrelated `UnifiedTimerHome.test.tsx` failure) before and after, plus `npx tsc --noEmit` and `npm run lint` clean, consistent with how the Tamagui-extraction fix (PR #789) was verified.
- Worth capturing new per-file timings (via `--reporter=json`) before/after Step 1 specifically, since the parallelism benefit depends on actual worker scheduling and should be confirmed rather than assumed.

---

## 7. Risks

- **Splitting `Map.test.tsx` might not yield the full expected parallelism win** if Vitest's scheduler already interleaves it efficiently with other files rather than leaving it as an isolated tail — the `maxWorkers=1` vs `4` comparison (96s vs 38s, ~2.5x not ~4x) is suggestive but not a direct measurement of "what happens if this one file becomes three." Verify with real timings during implementation before treating the win as proven.
- **Silently changing pointer-events assertions.** The biggest correctness risk in Step 2 — a careless mechanical migration could mask a test that currently (correctly) fails to interact with a disabled element, turning a real bug-catching test into a false pass. Requires the audit called out in Edge Cases, not just a blind find-and-replace.
- **Mock hoisting mistakes during the Map split.** `vi.mock()` ordering relative to the dynamic `await import('./Map')` is easy to get subtly wrong when copy-pasting across 3 files; a mistake here fails loudly (import errors / real maplibre-gl loading in jsdom) rather than silently, which is the safer failure mode but still worth flagging as the most likely implementation slip.

---

## 8. Open questions

- Exact filenames for the split `Map.test.tsx` pieces and the shared helper module — proposed above, open to whatever naming the team prefers (e.g. colocating helpers under `src/components/Map/__tests__/` instead of flat sibling files, if that's a preferred convention elsewhere in the codebase — a quick check didn't find an existing `__tests__/` convention here, so flat sibling files matching the existing `*.test.tsx` pattern seems consistent, but worth confirming).
- Whether Step 2's 149-call-site migration should be one mechanical PR or spread across incidental touches — recommended as one PR above, but this is a process preference rather than a technical constraint.
- Whether the Step 3 TamaguiProvider spike is worth scheduling at all, given it's the smallest and riskiest of the three opportunities relative to the ~5-10s (rough estimate, unverified) it might recover.
