# Character Linking Mechanics — Design Notes

*Captured from a design conversation, [date]. Status: exploratory, not yet scoped or balanced.*

## Origin idea
Map colours start at 0% saturation for new players/characters and rise toward 100% through activity — a permanent, one-way visual record of progress.

## Three separate mechanics (deliberately kept distinct — see "why separate" below)

### 1. Character efficacy / mood score
- Rises while a character is **linked** to a player, up to a maximum.
- **Decays while unlinked**, over a period of roughly a couple of months.
- Purely a function of *time linked*, not tied to specific player actions.
- Visible to the player as a score.
- Map saturation is one visual effect of this score (not a separate system).

### 2. Switch-cost points ("prestige points")
- Accrue on an **uncapped** scale while linked to a character.
- Spent when the player chooses to change character.
- When a player switches, there's a **24-hour grace window** where they can switch back to the previous character before its decay clock starts.
- Two distinct, independent elements — resolved after earlier confusion trying to make one number do both jobs:
  - **Minimum (gate)** — a fixed, authored value per character (or role), required before the player is eligible to switch away *from* that character at all.
    - **Rationale (decided):** reflects how much reward/depth that particular character or role offers the player — a richer role or a character with "a more interesting life" asks for more time before the player may leave, because the game wants them to actually experience what that character offers.
    - Explicitly **not** based on: number of past switches, the wider game economy, or role novelty to the player — those all belong to the price (below), not the gate.
    - Does **not** increase over the duration of a single link.
    - Not yet defined at the individual-character vs. role level — depends on the character role taxonomy, which doesn't exist yet (only conceptualised previously).
  - **Price (cost to switch to a specific destination)** — variable, advertised to the player when choosing a new character to switch to.
    - Can reflect: how novel the destination's role is to this player (first time in a role costs more), and/or economic supply needs (e.g. lower cost to switch into a role the game's economy is short on, as an incentive).
    - Free to flex/be tuned over time, unlike the fixed minimum.
  - **Unlock condition:** the moment a player first becomes eligible to switch (reaches minimum with current character), at least one destination character must be affordable/available — switching should never unlock into a dead end. The pool of viable destinations is expected to expand gradually as the player links with a more diverse range of characters.
  - **Post-minimum bonus multiplier:** once a player stays linked *past* the minimum, a bonus multiplier on points/rewards kicks in — the reward for choosing to linger rather than switching the instant they're eligible.
  - **After switching:** no separate reset mechanic — the player simply hasn't yet accrued points with the *new* character, and the price just spent is gone, so they naturally sit below that new character's minimum. Reaching it again before switching further is a byproduct of the existing accrual/spend rules, not an authored cooldown.

### 3. Link points
- **Permanent** — never spent, never decays.
- **Storage: decided — stored incrementally**, not calculated only on unlink. Driven by the requirement that players can always see their score accruing live; calculate-on-unlink would leave the displayed value stale until an unlink event.
- For **players**: contributes a multiplier to XP earned.
- For **characters**: acts as a permanent baseline-efficiency boost/multiplier — so a "reunion" character with a decayed mood score is still mechanically stronger than a fresh character, because this layer persists through mood decay.
- Feeds the post-minimum bonus multiplier in the switch-cost system (see above).
- Also currently feeds village points (existing use, to be reconciled).

## Why kept separate (not merged)
Considered merging switch-cost points and link points under one "link points" name, since spending switch-cost points felt conceptually simple. Rejected because:
- Link points are meant to be **permanent** (drives the persistent multiplier).
- Switch-cost points are meant to be **spent**.
- A single pool would mean switching characters silently weakens the permanent multiplier — undermining the "reunion character is genuinely stronger" idea.
- **Decision: keep three separate pools/values.** Simplest to reason about, protects the permanence guarantee.

## Open questions / not yet decided
- Character role taxonomy — doesn't exist yet, needed to define per-character/per-role minimums and role-novelty pricing. Only conceptualised previously.
- Exact formula for the fixed minimum per character/role (how "reward/depth" translates to a number).
- Exact formula for destination price (weighting of role novelty vs. economic supply incentives).
- Size of the post-minimum bonus multiplier, and how it scales with link points.
- Whether "unlinked" will ever apply pre-first-link (fresh characters) vs. only post-abandonment — current design assumes switching is deliberately costly/rare, so this is mostly a post-abandonment state.
- Balancing all of the above — explicitly deprioritized for now.

## Resolved since first draft
- Link points: stored incrementally (not calculated on unlink).
- Switch-cost is **two separate values**, not one escalating number: a fixed per-character minimum (gate) and a variable per-destination price (spent).
- Minimum does not increase with number of past switches, economy state, or role novelty — it's a fixed, authored reflection of that character's own value/depth.
- A post-minimum bonus multiplier rewards staying past the minimum, rather than the minimum itself escalating over time.
