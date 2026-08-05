# Issue #299: Compact/delete past character activities

## 1. High-level strategy

`CharacterActivity` rows are generated once per scheduled block per character per day (sleep, meals, work, etc. — see `character.services.behaviour_services.generate_day`) and never deleted. That's an unbounded, ever-growing table.

Critically, these rows are not just historical display data — `progression.models._character_skill_duration` (the shared base for `Role.proficiency_for`, `SkillGroup.proficiency_for`, `CharacterSkill.total_time/total_xp`, and `character_total_skill_xp`, which feeds the AP mastery multiplier on every future activity completion) live-aggregates `Sum("duration")` directly over `CharacterActivity` filtered by `character` + `activity_definition__skill`. Any compaction scheme has to keep feeding that aggregation, not just serve a read-only history view.

Approach: introduce a `CharacterActivityArchive` model holding one row per `(character, activity_definition, month)` — `total_duration` + `record_count` — and a periodic task that, for a rolling cutoff (e.g. activities completed more than N days ago), rolls matching `CharacterActivity` rows into archive rows and deletes the originals. `_character_skill_duration` (and thus every proficiency/mastery aggregate) is updated to sum across both `CharacterActivity` and `CharacterActivityArchive` for the same `(character, activity_definition__skill)` filter shape.

This keeps individual `CharacterActivity` rows for the recent window (so players still see a detailed activity feed, per the issue's explicit requirement), while older history collapses to one row per character/activity-type/month.

## 2. Files likely to change

- `progression/models.py` — new `CharacterActivityArchive` model; update `_character_skill_duration` to union live + archived durations. *(exists, extend)*
- `progression/migrations/000X_character_activity_archive.py` — new model + indexes. *(new)*
- `progression/tasks.py` — new periodic task `compact_character_activities`. *(new file — `progression` has no `tasks.py` yet; `character`, `users`, `gameplay`, `economy`, `locations`, `metrics` all follow this per-app `tasks.py` + `@shared_task` pattern)*
- `progress_rpg/celery.py` — new `beat_schedule` entry, same style as `generate_character_days_1am`. *(exists, extend)*
- `core/models.py` — optionally a `GameSettings.activity_compaction_cutoff_days` field (default e.g. 90), consistent with how `xp_mastery_scale`/`xp_mastery_multiplier_cap` were added for #691 rather than hardcoding the cutoff. *(exists, extend)*
- `progression/admin.py` — register `CharacterActivityArchiveAdmin` (read-only, matching the dormant-viewset/admin convention already used for other authored/aggregate models this epic added). *(exists, extend)*
- `progression/tests/test_models.py` or a new `progression/tests/test_activity_archive.py` — aggregation-with-archive-rows tests. *(extend or new, matching existing test file granularity)*
- `character/tests/test_tasks.py` — pattern already exists for `generate_character_days`; add a sibling test module or extend for the new task. *(new or extend)*

No changes needed to `CharacterActivityViewSet`/serializer/filters — archived months are intentionally not exposed there (recent-window detail view is unaffected); if a "monthly summary" read endpoint is wanted later that's a separate, follow-up concern, not required by this issue's acceptance criteria.

## 3. Implementation plan

1. Add `GameSettings.activity_compaction_cutoff_days` (default 90) with `clean()` validation (`> 0`), following the pattern of the #691 `xp_mastery_*` fields. Migration.
2. Add `CharacterActivityArchive` model: `character` FK, `activity_definition` FK, `month` (DateField, stored as first-of-month for a clean unique key), `total_duration` (PositiveIntegerField), `record_count` (PositiveIntegerField), unique constraint on `(character, activity_definition, month)`. Migration.
3. Update `_character_skill_duration` to sum `CharacterActivity` and `CharacterActivityArchive` separately (same filter shape translated to the archive's FK path) and add the two totals. This is the one part of the codebase every proficiency/mastery calculation funnels through, so it's the only place that needs to know both tables exist.
4. Write `progression/tasks.py::compact_character_activities`:
   - Determine cutoff = `now - GameSettings.current().activity_compaction_cutoff_days`.
   - For completed `CharacterActivity` rows with `completed_at < cutoff`, group by `(character_id, activity_definition_id, month)` via `.values(...).annotate(Sum("duration"), Count("id"))`.
   - For each group, `get_or_create`/`update_or_create` the matching `CharacterActivityArchive` row, incrementing `total_duration`/`record_count` (so re-runs against a partially-processed month are additive-safe, not overwrite-only — see concurrency notes).
   - Delete the source `CharacterActivity` rows for that group only after its archive row is confirmed written, inside a transaction per group (not one giant transaction for the whole table) to bound lock time and allow partial-failure resumption.
   - Use `.iterator(chunk_size=...)` for the grouped queryset, matching `generate_character_days`'s batching convention.
5. Register the task in `progress_rpg/celery.py` `beat_schedule`, e.g. daily off-peak (`crontab(hour=3, minute=0)`), after the 1am generation/metrics jobs.
6. Add `CharacterActivityArchiveAdmin` (read-only `list_display`/`list_filter` on character/month), matching the existing admin conventions in this file.

## 4. Design decisions

- **Archive granularity: per (character, activity_definition, month), not per (character, activity_definition__skill, month).** Keeping `activity_definition` as the grouping key (rather than pre-aggregating to skill) preserves enough structure to answer both "skill XP for this skill" and "time spent per specific activity" without baking in the skill relationship at write time — if `ActivityDefinition.skill` is later reassigned, archived rows don't need to be rewritten, since `_character_skill_duration` joins through `activity_definition__skill` at query time. *Alternative considered:* grouping straight to `(character, skill, month)` — rejected, it's a small aggregation-time cost saved in exchange for losing the ability to show "time by activity" for archived months at all (issue explicitly wants individual rows kept for the live window and implies future analytics use archived-month rollups by activity, not by skill).
- **Deletion cutoff via `GameSettings`, not hardcoded.** Consistent with how #691 made the AP formula's tunables (`xp_mastery_scale`, `xp_mastery_multiplier_cap`) live settings instead of constants. *Alternative:* Django setting/env var — rejected, `GameSettings.current()` is the established pattern for this kind of runtime-tunable value in this codebase already.
- **Additive `update_or_create` per group, not delete-then-recreate.** A group's archive row may already exist from a previous run (e.g. task re-triggered, or a month straddles two runs as more activities complete and age past the cutoff). Summing into the existing row keeps re-runs idempotent-safe without needing a "have I processed this row" marker column.
- **Not deferring to a `django-tasks`/one-off management command instead of Celery beat.** Every other periodic maintenance job in this codebase (`generate_character_days`, `reconcile_stale_online_players`, `calculate_daily_metrics`, etc.) is a `@shared_task` + beat schedule entry — matching that is "reuse existing architecture" rather than introducing a new execution model.
- **Not touching `CharacterActivityViewSet`.** The issue's stated goal is storage reduction while keeping the *recent* detail feed intact; it does not ask for a "browse archived months" UI. Adding one now would be scope creep beyond the acceptance criteria — can be a follow-up issue if wanted.

## 5. Edge cases

- **In-progress (`is_complete=False`) activities:** never included in compaction grouping — only `completed_at < cutoff, is_complete=True` rows are candidates. An activity that started before the cutoff but hasn't completed yet must survive.
- **Character/ActivityDefinition deletion:** `CharacterActivity.character` is `CASCADE` and `activity_definition` is `PROTECT`. Archive rows should mirror this — `character` `CASCADE` (a deleted character's archived history should go with it, same as its live rows do today) and `activity_definition` `PROTECT` (an authored definition can't be deleted out from under archived aggregates, same protection the live table already has).
- **Partial task failure mid-run:** processing per-group in its own transaction means a crash partway through only risks re-processing the last incomplete group (safe, since archive writes are additive) — not the whole batch.
- **Concurrent compaction runs** (e.g. retried Celery task overlapping a slow prior run): guard with `select_for_update()` on the `CharacterActivity` rows being grouped/deleted per group, matching the locking pattern already used in `behaviour_services.py` (`CharacterActivity.objects.select_for_update()`), so two overlapping runs can't double-delete/double-count the same rows.
- **Migration/backfill of existing production data:** the first run of this task against the existing table could touch a very large number of rows at once. Worth capping how far back the *first* run compacts (e.g. process one month-cohort per invocation, oldest-first) rather than assuming a single run clears the entire backlog — flagged as an open question below rather than decided here.
- **`character_total_skill_xp` recalculation cost:** it's called on every `CharacterActivity.complete_now()`/`complete_past()` to compute the mastery multiplier. Adding a second aggregate query (against the archive table) roughly doubles that cost per completion. Should stay cheap given both queries are indexed sums, but worth confirming with a query-count assertion in tests, not just a functional one.

## 6. Tests

- `_character_skill_duration` (and by extension `Role.proficiency_for`, `character_total_skill_xp`, `CharacterSkill.total_time/total_xp`) returns the correct combined total when duration is split across live `CharacterActivity` rows and `CharacterActivityArchive` rows for the same character/skill.
- `compact_character_activities`: rows older than the cutoff are archived and deleted; rows newer than the cutoff are left untouched; in-progress rows are never touched regardless of age.
- Re-running the task against a month already partially archived accumulates `total_duration`/`record_count` correctly rather than double-counting or overwriting.
- Grouping correctness: activities across two different `activity_definition`s in the same month for the same character produce two distinct archive rows, not one merged row.
- `CharacterActivityArchive` FK behavior: deleting a `Character` cascades to its archive rows; attempting to delete an `ActivityDefinition` referenced by an archive row is blocked (`PROTECT`), matching existing `CharacterActivity` behavior — extend rather than duplicate the existing FK-behavior tests if any exist for `CharacterActivity`.
- Query-count assertion on `character_total_skill_xp` / `get_xp_reward_summary` post-change, to catch the aggregation becoming more expensive than intended.

## 7. Risks

- Forgetting to update *all* consumers of `_character_skill_duration` — it's a single shared helper, so this is low-risk by construction, but any code that queries `CharacterActivity` directly for a duration/XP total *outside* that helper (worth a fresh grep at implementation time) would silently under-count once compaction starts running.
- Off-by-one on the cutoff boundary (`completed_at < cutoff` vs `<=`, and month-bucketing using `completed_at` vs `scheduled_end`) — should pick one field consistently and document why (recommend `completed_at`, since `scheduled_end` can differ for activities completed late via `complete_past()`).
- Running the first compaction pass against a large existing production backlog inside one Celery task invocation without a batch/resume cap, risking a long-running task or timeout (see edge case above).

## 8. Open questions

- What cutoff should `activity_completion_cutoff_days` default to (issue says "past month" as an example, not a firm number)?
- Should the very first backfill run against existing production data be a one-off management command (bounded, observable, re-runnable manually) rather than letting the first beat-scheduled run process the entire historical backlog at once?
- Is there any product requirement to ever surface archived months to players/admins (e.g. "time spent per month" summary), or is this purely a backend storage concern for now? Affects whether `CharacterActivityArchive` needs a serializer/endpoint at all.
