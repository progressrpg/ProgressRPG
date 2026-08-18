# Plan: migrate DetailSurface off Radix Dialog (#799)

## 1. High-level strategy

`DetailSurface.tsx` is the last file under `frontend/src` importing
`@radix-ui/react-dialog` directly (confirmed by grep). It has exactly two
consumers with genuinely different needs, and the split matters for how
this should be built:

- **`DetailCard`** → `DetailSurface` with `modal` defaulted to `true`, no
  `container`. Not currently mounted anywhere live in the app (grep finds
  no `<DetailCard` usage outside its own files), but it is tested and
  storied, so it must keep working.
- **`MapDetailCard`** → `DetailSurface` with `modal={false}` and
  `container={mapWrapperEl}` (the map's own wrapper element), always. Both
  live call sites are in `Map.tsx` (character and building detail cards).

The modal/no-container path is a direct application of the pattern already
established twice in this codebase (`Modal.tsx`, `AlertDialog.tsx`) - low
risk, no new ground. The non-modal/container path is genuinely new:
verified empirically (real render, not just reading source) that Tamagui's
`Dialog` always portals to `document.body` via `@tamagui/portal`'s `Portal`,
regardless of the `modal` prop - there is no per-instance container
override, unlike Radix's `Dialog.Portal`. Confirming this by direct test
mattered: a naive read of `@tamagui/dialog`'s source suggests non-modal
dialogs skip the portal entirely and render inline, which turned out not to
match what actually renders.

Land as two separate, independently reviewable commits along that same
split, per the existing convention on every PR in this migration chain.

## 2. Files likely to change

- `frontend/src/components/DetailSurface/DetailSurface.tsx` (existing) -
  the only real change. Swaps the Radix import for Tamagui's `Dialog`, adds
  the container-portal handling for the non-modal case.
- `frontend/src/components/DetailSurface/DetailSurface.test.tsx` (existing)
  - extend with container-portal and focus-restore coverage (see
  [Tests](#6-tests)); existing assertions (role, accessible name, Escape)
  should keep passing unmodified.
- `frontend/package.json` / `package-lock.json` (existing) - drop
  `@radix-ui/react-dialog` once nothing imports it, same as #587 did for
  the other three.
- `frontend/docs/RADIX_TO_TAMAGUI_A11Y_CHECKLIST.md` (existing, from #587)
  - update once this lands: mark #799 resolved, record this change's real
  bundle-size delta (unlike #587's three removals, `react-dialog` **is**
  currently bundled since it's actually used - expect a real, non-zero
  number here, not the 0-byte result those three had).
- **No changes needed** to `MapDetailCard.tsx`, `DetailCard.tsx`, or
  `Map.tsx` - all three already only depend on `DetailSurface`'s existing
  `open`/`onOpenChange`/`title`/`children`/`modal`/`container` props, which
  is exactly the contract `DetailSurface`'s own header comment describes
  and is not changing.
- No new files anticipated - see [Design decision B](#4-design-decisions)
  for why the container-portal logic stays inside `DetailSurface.tsx`
  rather than a new helper.

## 3. Implementation plan

1. **Modal-mode swap** (covers `DetailCard`'s usage: `modal=true`, no
   `container`). Port directly using the `Modal.tsx`/`AlertDialog.tsx`
   pattern: `<Dialog open onOpenChange={...}>`, `<Dialog.Portal
   role="presentation">` (strips the double-`dialog`-landmark issue those
   two already solved), `<Dialog.Overlay unstyled>` when `modal`,
   `<Dialog.Content unstyled onCloseAutoFocus={...} onInteractOutside={...}>`,
   `<Dialog.Title asChild><h2 className="sr-only">`. Adopt
   `useReturnFocusOnClose` (existing hook, already used by both Modal and
   AlertDialog for exactly this reason: no `Trigger` element in the tree,
   so Tamagui's own focus-restore-to-trigger silently no-ops).
   `DetailSurface.test.tsx`'s existing assertions should pass unchanged
   after this step; `DetailCard.test.tsx` should too.
2. **Non-modal + container swap** (covers `MapDetailCard`'s usage). When
   `container` is supplied, skip `<Dialog.Portal>` and instead portal
   `<Dialog.Content>` (no `<Dialog.Overlay>` - already conditional on
   `modal` today, keep it that way) via `ReactDOM.createPortal(content,
   container)` directly, keeping it a React-tree descendant of `<Dialog>`
   so context (open state, dismissable wiring, focus scope) still
   propagates through the portal boundary - `createPortal` only changes
   DOM placement, not React context. Preserve the existing
   `onInteractOutside={(e) => { if (!modal) e.preventDefault(); }}` logic
   unchanged.
3. **Real-render verification** against the actual `Map` page (not just
   unit tests) for both `MapDetailCard` call sites - open a character
   detail card and a building detail card, confirm the panel docks inside
   the map wrapper at the expected position, and resize the window to
   confirm it stays docked. This is exactly the class of thing jsdom can't
   catch (see [#799](https://github.com/progressrpg/ProgressRPG/issues/799)'s
   own reasoning for why this couldn't be done in that investigation's
   sandbox).
4. **Drop the dependency**: remove `@radix-ui/react-dialog` from
   `package.json`, run `npm install`, confirm `grep -rn "@radix-ui"
   frontend/src` returns nothing but the existing `Tabs.tsx` comment,
   rebuild and record the real bundle-size delta.
5. **Close the loop on #587**: update
   `docs/RADIX_TO_TAMAGUI_A11Y_CHECKLIST.md`'s "Remaining Radix usage"
   section to mark this resolved, with the bundle delta from step 4 and a
   note on the real-render verification from step 3.

## 4. Design decisions

**A. Two phases (modal, then non-modal+container), not one combined
change.**
- Alternative: do the whole file in one pass.
- Chosen because the two paths carry very different risk. The modal path
  is a copy of an already-proven pattern (twice over); the non-modal path
  is genuinely new engineering with an unverified risk (see
  [Risks](#7-risks)). Splitting means the low-risk half can land and be
  reviewed on its own, and isolates review attention on the part that
  actually needs it - consistent with every other PR in this migration
  chain landing as a small, focused diff.

**B. Manual `createPortal(content, container)` inside `DetailSurface.tsx`,
bypassing `Dialog.Portal` only for the container case.**
- Alternatives considered:
  - *Reimplement `Dialog.Portal`'s internals wholesale* (its exit-animation
    timing, z-index stacking, native-`<dialog>` `show()`/`close()` calls) so
    it can accept a container. Rejected: needless duplication for a single
    consumer, the reimplementation itself would be the highest-risk part of
    this whole change, and the planning template's own guidance is to avoid
    unnecessary abstraction/complexity.
  - *Accept the `document.body`-portal default and reposition the docked
    panel with `getBoundingClientRect()` on the map wrapper instead of
    relying on DOM containment.* Rejected as first choice: changes the DOM
    structure (panel becomes a body-level sibling of the map, not a
    descendant), which likely breaks CSS in `MapDetailCard.module.scss`
    written against DOM containment (needs checking - see
    [Open questions](#8-open-questions)) and adds a resize/scroll-tracking
    concern that DOM containment never had. Worth keeping in reserve if
    step 2 turns out to have a hidden blocker (see Risks).
- Chosen because it's the smallest real change: `Dialog.Content`/`Overlay`
  still do the actual work (focus trap, dismissable layer, ARIA - all live
  in `Content`, not `Portal`), and React context isn't affected by where a
  subtree is portaled to, so the open/close wiring from `<Dialog>` (Root)
  keeps working unmodified.

**C. Reuse `useReturnFocusOnClose` rather than writing DetailSurface's own
version.**
- Alternative: hand-roll focus capture/restore specific to DetailSurface.
- Chosen because it's a direct fit, not an adaptation: DetailSurface, like
  Modal and AlertDialog, has no `Trigger` in its tree (`open` is a
  controlled prop), so Tamagui's own trigger-based restore is a no-op here
  for exactly the same reason documented in that hook's own comment.

## 5. Edge cases

- **`container` becomes `null`** (e.g. the map wrapper ref hasn't resolved
  yet, or unmounts while the dialog is open) - `createPortal(children,
  null)` throws. `container`'s existing type is already `HTMLElement |
  null`; the non-modal path needs an explicit guard (e.g. don't render, or
  fall back to Dialog's own default portal) rather than crashing on a null
  container mid-render.
- **`onInteractOutside`'s modal-only gating** - preserve the existing exact
  conditional (`if (!modal) e.preventDefault()`) rather than rederiving it;
  getting this backwards would make the docked panel either trap outside
  clicks it shouldn't, or let a real modal dismiss on outside click when it
  shouldn't.
- **Switching between character and building detail** in `Map.tsx` (only
  one `MapDetailCard` renders at a time, gated by `detail?.type`) - confirm
  `useReturnFocusOnClose`'s capture-on-open logic still fires correctly
  across that transition (closing one and opening the other in the same
  tick), not just a clean open→close→open cycle.
- **Overlay stays conditional on `modal`** - `DetailSurface` already only
  renders `<DialogPrimitive.Overlay>` `{modal && ...}`; keep that condition
  exactly, don't let it leak into the non-modal portal path.

## 6. Tests

- Existing `DetailSurface.test.tsx` assertions (role=dialog, accessible
  name from title, Escape calls `onOpenChange(false)`) must keep passing
  unmodified in behavior.
- New: with a `container` prop, `Dialog.Content` renders as a DOM
  descendant of that container element (assert via
  `container.contains(...)`, jsdom-testable) - plus a case for
  `container == null` not crashing.
- New: `modal={false}` renders no overlay, and a click outside the surface
  does not dismiss it (mirrors `AlertDialog.test.tsx`'s existing "does not
  close when clicking outside" test, but inverted expectation for the
  non-modal case - and unlike that test, no `pointerEventsCheck: 0`
  workaround should be needed here precisely because non-modal shouldn't be
  blocking outside pointer events at all).
- New: focus returns to whatever had focus before opening, once closed
  (mirrors `AlertDialog.test.tsx`'s existing "restores focus to the
  previously focused element on close" test).
- `DetailCard.test.tsx` and `MapDetailCard.stories.tsx` should keep passing
  unmodified - if either needs a change to pass, that's a signal something
  in this plan's assumptions about their contract with `DetailSurface` is
  wrong.
- Real-browser (Playwright) verification is necessary but not sufficient
  on its own for the container/positioning behavior - see step 3's
  real-render-against-Map recommendation, which no test suite here can
  substitute for.

## 7. Risks

- **Biggest one**: `Dialog.Content`'s exit-animation/presence timing may be
  wired through `Dialog.Portal`'s own `Animate`/`onExitComplete` machinery
  rather than living in `Content` itself - if so, bypassing `Dialog.Portal`
  for the container case could break the closing transition (content
  vanishing instantly, or internal `isFullyHidden` state never resolving,
  which could affect `keepChildrenMounted` semantics). This needs checking
  against a real render during implementation - don't assume either way
  from source alone (the empirical test run during this planning pass
  already contradicted one source-reading-based assumption once).
- **CSS written against Radix's exact DOM/attribute shape**: both
  `MapDetailCard.module.scss` and `DetailSurface.module.scss` weren't
  reviewed in this pass for selectors keyed off Radix-specific data
  attributes (e.g. `[data-state="open"]`). Tamagui's Dialog does set
  matching attributes elsewhere in this migration ("adapted from
  radix-ui"), but confirm against these two specific stylesheets rather
  than assuming parity from the Modal/AlertDialog precedent.
- **Treating this as "just like Modal.tsx"** for the whole file and
  under-scoping the non-modal+container half as a copy-paste - it isn't;
  that half is genuinely new engineering per Design decision B.
- **`onInteractOutside`/focus-trap subtleties differing between Radix and
  Tamagui's `Dialog`** beyond what's already been surfaced elsewhere in
  this migration (e.g. AlertDialog's #582 PR) - worth a final read of
  `@tamagui/dialog`'s actual shipped behavior for the non-modal case
  specifically, since that's the one path this migration hasn't exercised
  before now (Modal and AlertDialog are both always-modal).

## 8. Open questions

- Does `MapDetailCard.module.scss` or `DetailSurface.module.scss` rely on
  any Radix-specific data attribute or DOM shape that needs confirming
  Tamagui's `Dialog` also produces? Not checked in this planning pass.
- Is keeping both the modal and non-modal+container code paths inside one
  `DetailSurface.tsx` still the right call once the non-modal path's actual
  implementation is in hand, or does it turn out cleaner to give
  `MapDetailCard` its own thin non-modal-specific wrapper? Current
  recommendation is to keep one file, matching the "only this file imports
  a UI primitive" contract `DetailSurface`'s own header comment already
  establishes - but this is worth a second look once step 2's real shape is
  known, since it would roughly double this file's responsibility.
- Worth a quick check of whether a newer Tamagui release (currently pinned
  `^2.7.6`) has added a per-instance Portal container override since this
  plan was written - would remove the need for step 2's manual portal
  entirely, and is a cheaper check than building the workaround first.
