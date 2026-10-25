# Plan: #592 — Extract design tokens into a platform-neutral TS module

Epic #588. Absorbs #641 (closed). Blocks #593, #594, #596, #597, #598.

## 1. High-level strategy

- **TS becomes the single authored source** for primitive and semantic design tokens, in a new `frontend/src/tokens/`.
- **A generator script** turns that source into two committed outputs:
  - **Sass partials** that keep every existing variable and map name. The 65 dependent modules then compile untouched.
  - **A resolved TS module** (literal values only) for runtime consumers: `tamagui.config.ts`, and later anything on native.
- **Derived colours are computed by the `sass` package itself** inside the generator, not by hand-written HSL maths. The same engine that produces today's CSS produces the new literals, so parity comes by construction rather than by tuning rounding.
- **Built CSS must stay byte-identical.** Each step is gated by a before/after diff of the production CSS.
- **Last step:** `tamagui.config.ts` swaps Tamagui's stock colour, space and font tokens for the generated ones, and `Map/layers.ts` drops its hand-copied `#ff8800` (the "one real consumer").

Verified up front (2026-10-25, Dart Sass 1.103.1, the project's installed version):

- `color.adjust` output serialises as fractional `rgb(0%, 52.84…%, 21.65…%)`, not hex. The hex values quoted in source comments (e.g. `#00943c`) are approximations of what actually ships.
- Writing that serialised string back as a literal round-trips byte-for-byte. That holds both when emitted directly and when fed through later `rgba(…, 0.08)` and `color.adjust` calls. Emitting resolved literals into the generated Sass is therefore safe; the full-build diff remains the real gate.

## 2. Files likely to change

| File | New? | Why |
|---|---|---|
| `frontend/src/tokens/primitives.ts` | new | Base colours, scale recipes (lightness deltas per step), neutral scale literals, spacing, typography maps, breakpoints, z-index, durations/easing. Typed. |
| `frontend/src/tokens/semantic.ts` | new | Semantic colour/spacing tokens and the `$text-tone` / `$button-variants` / `$list-variants` data, expressed as references to primitives. |
| `frontend/src/tokens/resolved.generated.ts` | new, generated | Literal values for runtime use. Colours as 6/8-digit hex (native-safe). |
| `frontend/src/tokens/index.ts` | new | Public entry point. Re-exports the resolved values and types. App code imports only this. |
| `frontend/scripts/generate-tokens.ts` | new | Generator, with a `--check` mode that fails if committed output is stale. Runs on Node 22 type-stripping, so no `tsx` dependency is needed. |
| `frontend/src/styles/tokens/_colors.scss`, `_spacing.scss`, `_typography.scss` | existing → generated | Contents replaced by generated literals with the same names, maps and key spelling, plus a "generated, do not edit" header. |
| `frontend/src/styles/base/_variables.scss` | existing → generated | Same treatment. |
| `frontend/src/styles/semantic/_colors.tokens.scss`, `_spacing.tokens.scss` | new, generated | Data half of the semantic partials. |
| `frontend/src/styles/semantic/_colors.scss`, `_spacing.scss` | existing | Keep the mixins and `token()` function; replace the data with `@forward` of the generated partial. |
| `frontend/package.json` | existing | Add `tokens:generate` and `tokens:check` scripts. |
| `.github/workflows/type-check.yml` | existing | Run `tokens:check` in the `typescript` job. (Its Node 20 → 22 bump, needed for type-stripping, is already done on this branch.) |
| `frontend/tamagui.config.ts` | existing | Consume generated tokens. Build `media` from the breakpoint tokens. (The header comment already points to #592, fixed on this branch.) |
| `frontend/src/components/Map/layers.ts` | existing | Import the accent colour instead of hard-coding `#ff8800`. |
| `frontend/src/tokens/__tests__/*.test.ts` | new | See §6. |

**Not changed:** `semantic/_typography.scss` (the `$text-*` style maps). See decision D5.

## 3. Implementation plan

Each step is a commit. Steps 1–4 can be one PR; step 5 is a second PR.

0. **Capture the baseline.** Build `development` with `build:production` and save the concatenated `dist/assets/*.css`, sorted by asset name with hashes stripped. Doing this by hand each time is enough; don't build tooling for it unless it gets painful.
1. **Primitives in TS + generator for `tokens/` and `base/_variables`.**
   - Author `primitives.ts`.
   - The generator compiles a throwaway SCSS snippet through `sass.compileString` to resolve each `color.adjust` recipe.
   - It then writes the four Sass partials as literals and writes `resolved.generated.ts`.
   - Diff the built CSS: it must be identical.
2. **Semantic data in TS.**
   - Author `semantic.ts`.
   - Generate `semantic/_*.tokens.scss`, and slim `_colors.scss` / `_spacing.scss` down to `@forward` plus their mixins and functions.
   - Diff the built CSS: it must be identical.
3. **Stale-output check.** Add the `tokens:check` npm script and the CI step. CI already runs Node 22.
4. **Unit tests** (§6).
5. **Runtime consumers (separate PR, so it reverts cleanly if Tamagui output shifts).**
   - `tamagui.config.ts` replaces `tokens.color`, `tokens.space`, `tokens.radius` and `tokens.zIndex`, plus `fonts`, with generated values; `size` stays stock (D6).
   - `media` is derived from the breakpoint tokens.
   - `Map/layers.ts` imports the accent colour.
   - Visually check every Tamagui component that is *not* `unstyled` (see the Risks section).

## 4. Design decisions

**D1. TS is authored; Sass is generated (rather than Sass consuming JSON at build time).**
- Alternative: a Vite/Sass importer that reads JSON. That leaves no committed Sass to diff, adds build-time magic, and still needs a path to the TS runtime.
- A committed generated file makes every token change reviewable and keeps the Sass build unchanged.

**D2. Derive scales with the `sass` engine in the generator, and commit the literals (#641's "derived at build time").**
- Alternative A: precompute by hand. This loses "the base colour is the knob" and repeats the hand-copying #641 objected to.
- Alternative B: reimplement `color.adjust` in JS. This risks rounding drift, the exact failure #592 warns about.
- Using `sass` (already a devDependency) gives identical maths for free.

**D3. Generated Sass holds resolved literals, not reproduced `map.get` / `color.adjust` expressions.**
- Alternative: emit expressions mirroring today's source. That guarantees parity but needs a reference DSL in the TS tokens, which is more abstraction.
- The spike in §1 shows literals round-trip exactly, so the simpler option wins. If the full diff disagrees, fall back to emitting expressions for the affected tokens only.

**D4. Runtime gets hex; Sass gets Sass's own serialisation.**
- Native can't parse `rgb(52.84%…)`, and out-of-gamut values like `hsl(145, 100%, 105%)` (see the Edge cases section).
- Both come from the same computed colour, so this is one source with two encodings. The precision difference is below 8-bit and isn't visible.

**D5. Leave `semantic/_typography.scss`'s `$text-*` style maps to #593.**
- They exist only to feed `apply-text-style`, and #593 has to reshape them for a runtime breakpoint system anyway.
- Moving them twice is waste. The primitive typography maps (`$font-size` etc.) *do* move here, so #593 has tokens to reference.
- Alternative: move them now, as #592's body lists them. That's possible, but doubles the parity surface for no consumer.

**D6. Replace Tamagui `color` / `space` / `radius` / `zIndex` / `fonts`; keep stock `size` and `themes`.**
- The acceptance criteria name colour, spacing and typography.
- The app has no `size` scale, so replacing it would change Tamagui's internal component dimensions.
- No component reads theme values today: no `$token` props or `useTheme` anywhere. Theme rework belongs with #594 / #596, when components start using Tamagui styling.

**D7. Author spacing and font sizes as unitless px numbers.**
- The generator emits `rem` (÷16) for Sass, and Tamagui and native take the numbers.
- Alternative: author rem strings and parse them for native. Numbers are the platform-neutral form, and every current value divides exactly (e.g. 10 → `0.625rem`).

## 5. Edge cases

- **Sass map keys are numbers, not strings.**
  - `050` and `50` are the same key. `$secondary-scale` uses `050`, but `$color-bg` looks it up with `50`; `$dark-scale` uses `50`.
  - `2xl` is the number 2 with unit `xl`.
  - The generator must emit keys unquoted, exactly as authored. Quoting them would make `map.get` return null and silently drop declarations.
- **Out-of-gamut `$color-bg`.** `$secondary-scale` 050 (+10% lightness on an already ~95% colour) resolves to `hsl(145, 100%, 105.29%)`. Browsers clamp it to white. Preserve it in Sass for parity and emit clamped `#ffffff` for runtime. The fix is tracked in #857, to land after this.
- **Anomalies to preserve, not fix (they belong to #594):**
  - `$list-variants.default.tone: base` (no such tone, so it resolves to null).
  - The unused `hover` keys.
  - `font-weight: normal` lookups in `semantic/_typography.scss`, a missing key that also resolves to null. That file doesn't move here (D5), but don't "fix" it.
- **Non-colour values must pass through verbatim:**
  - `rgba(0, 0, 0, 0.15)`
  - shadow lists
  - the font-family list `('Roboto', sans-serif)`
  - space-separated padding pairs
  - `ease-in-out`
- **Downstream maths on generated literals.** `rgba($x, 0.08)` and `color.adjust` inside modules and in `utilities/_tier-colors.scss` operate on the literal rather than the full-precision value. The spike shows this is identical at Sass's 10-digit precision; the full-build diff confirms it.
- **The generator isn't deterministic unless forced.** Fix the key order (insertion order from the TS objects), number formatting and line endings (LF). Remember Windows checkouts over UNC paths.
- **Partial failure.** The generator writes all outputs or none: render everything in memory, then write. A failing `--check` names the stale file.
- **No concurrency, data or migration concerns.** This is build-time only.

## 6. Tests

New (Vitest, unit project):

- **Generator check:** running the generator in memory yields output identical to the committed files. This duplicates the CI check deliberately, so it fails locally too.
- **Scale derivation:** spot-check a few resolved scale values against the Sass-computed serialisation, e.g. primary 400 and dark 50.
- **Runtime hex:** every resolved runtime colour matches `^#[0-9a-f]{6}([0-9a-f]{2})?$`.
- **Breakpoints:** `tamagui.config.ts` media `sm`/`md`/`mdUp` equal the breakpoint tokens. This replaces the "verify against `_variables.scss`" criterion.
- **Map keys:** generated Sass contains unquoted keys `050`, `2xl` and `000`. This is a regression guard for the null-lookup trap.

Existing: there are no unit tests for styles. Leave the Playwright and a11y suites untouched; they're the regression net for step 5. Per CLAUDE.md, Claude runs only the new test files; Duncan runs the full Vitest and Playwright suites.

Manual:

- Byte-identical CSS diff at steps 1 and 2.
- For step 5, before/after screenshots of the Tamagui components that render default frames (see the Risks section).

## 7. Risks

- **Quoting map keys**, as the Edge cases section describes. This is the easiest silent break, and only the CSS diff or a missing style would reveal it.
- **"Fixing" the anomalies** while moving them. That breaks byte-identity and drags #594 scope in. Preserve, then note them.
- **Hand-editing a generated `.scss` file.** The header plus `tokens:check` in CI catches it; make sure the header says to edit `src/tokens/` instead.
- **Tamagui components that aren't `unstyled`** still render theme and token-driven defaults: `Tabs` content (`Tabs.tsx` ~l.131) and Modal's inner element (`Modal.tsx` ~l.73). Swapping `space` / `radius` / `color` can shift them, so check them by eye in step 5.
- **Tamagui token-shape requirements.** `space` needs a `true` default key and negative variants are generated, while `zIndex` and `radius` have their own expectations. Build with `createTokens` and let type errors guide the shape. Don't hand-merge into `defaultConfig.tokens` field by field.

## 8. Open questions

1. **D5 scope split.** Should the `$text-*` style maps move here or in #593? If here, the #592 acceptance criteria need no edit; if #593, add a note to both issues.
2. **Should the epic stay active?** The 2026-10-25 review found no movement since 2026-08-23. Confirm #588 is still prioritised before starting this L-sized item.

Resolved 2026-10-25:

- The out-of-gamut `$color-bg` is filed as #857.
- CI moved to Node 22: `type-check.yml` and `deploy-docs.yml`; `main.yaml` was already on 24.

## 9. Implementation notes (2026-10-25)

Implemented on `chore/592-design-token-plan`. Where it departs from the plan above:

- **`semantic/_spacing.scss` is generated in place.** It holds no mixins, so it didn't need a `.tokens.scss` split. Only `semantic/_colors.scss` is split: it keeps `token()` and the three mixins, and forwards `_colors.tokens.scss`.
- **Tamagui `radius` and `zIndex` stay stock (D6 revised).** Tamagui requires space/radius/zIndex keys to be a subset of the `size` keys. `size` stays stock, so the app's named keys are rejected. `space` is keyed by step instead (`$1` = xs … `$7` = 3xl).
- **Tamagui fonts stay stock; the acceptance criterion for typography is not met yet.** Swapping them is a visible change, not a token move:
  - AlertDialog's Title/Description render Tamagui's heading/body styles, so the title would go from 32px/700 to 18px/600.
  - Tamagui's wrapper elements set the inherited font, so portal text would move from the Inter/system stack to Roboto.

  That is a design decision for its own issue.
- **Verification** (beyond the unit tests):
  - Production CSS is byte-identical to `development` across all 22 assets. A one-step colour mutation was confirmed to show up in the same comparison.
  - In Storybook, the computed styles of every element across 13 Modal/AlertDialog/Toast/Tooltip/ProgressBar/TutorialModal stories are unchanged, excluding CSS custom properties, at a matching device pixel ratio.
  - Pitfall: the ratio changes when the browser pane is hidden or shown, and that alone shifts every border width.
- **D5 went as recommended.** The `$text-*` style maps stay in `semantic/_typography.scss` for #593.
