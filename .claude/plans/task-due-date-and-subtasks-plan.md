# Extend Task model: due date + parent/child subtasks

## Context

Tasks now live inside the timer's Planning mode (`UnifiedTimerHome` → `TasksPanel`, see the unified-timer-task-mode work), and the next step is making the Task model richer: a due date, and the ability to break a task into subtasks. This plan adds both end-to-end — backend model/API through to a fully nested subtask UI — since `PlayerItemList` (the shared list component behind `TasksPanel` and `ProjectsPanel`) currently has zero grouping/nesting support, and building it now unblocks subtasks rendering as an actual indented tree rather than a flat annotated list.

`UnifiedTimerHome` already renders `<TasksPanel />` directly and unmodified inside Planning mode (from the prior mode-switch work) — since this plan extends `TasksPanel`/`useTasksPanel` in place rather than forking them, every capability added here (due-date editing, the parent picker, the "add subtask" row action, nested subtask rendering) is automatically available from Planning mode too, with no separate integration step.

Decisions already confirmed with the user:
- **Due date**: one field, `due_at` (DateTimeField), not separate date/time fields — matches the codebase's existing convention (every date/time field in the app is a DateTimeField; no bare DateField anywhere; closest precedent is `CharacterActivity.scheduled_start`/`scheduled_end`). Displayed as a single `datetime-local` input.
- **Subtasks**: single level only — a task with a `parent` cannot itself have subtasks (enforced server-side). No arbitrary-depth trees, no cycle detection needed beyond "reject nesting a subtask under a subtask."
- **Parent deletion**: cascades — deleting a parent deletes its subtasks (`on_delete=CASCADE`).
- **fetchTasks pagination bug**: `frontend/src/api/tasks.ts`'s `fetchTasks()` only fetches page 1 today. This must be fixed as a prerequisite — subtask grouping needs the full flat list, and a parent on page 2+ would silently lose its children in the UI otherwise.
- **Add-subtask flow**: a row action on a top-level task pre-fills the existing "add task" form with that task as the parent (one creation code path, no separate dialog).
- **Hide-complete rule**: parent-scoped — a completed parent (and all its subtasks, regardless of their own status) disappears as one unit when "Hide complete" is on; an incomplete, visible parent shows each subtask independently based on its own completion.
- **Overdue styling**: minimal — red/warning style on the due-date meta text when `due_at` is in the past and the task isn't complete.
- **Rollup**: a parent task's `total_time` must include its subtasks' time, not just its own directly-linked activities (a parent is a container for its children's work as well as any of its own). `total_records` stays own-only (not requested) — flagged explicitly below so this isn't silently extended beyond what was asked.

---

## Backend

### 1. Model (`progression/models.py`, `Task` class, ~line 648)

```python
due_at = models.DateTimeField(null=True, blank=True)
parent = models.ForeignKey(
    "self", on_delete=models.CASCADE, related_name="subtasks",
    null=True, blank=True,
)
```

Add `Task.clean()` as the single source of validation truth:

```python
def clean(self):
    super().clean()
    if self.parent_id is None:
        return
    if self.parent_id == self.id:
        raise ValidationError({"parent": "A task cannot be its own parent."})
    if self.parent.parent_id is not None:
        raise ValidationError({"parent": "Cannot nest more than one level deep."})
    if self.parent.player_id != self.player_id:
        raise ValidationError({"parent": "Parent task must belong to the same player."})
    if self.pk and self.subtasks.exists():
        raise ValidationError({"parent": "A task with subtasks cannot itself have a parent."})
```

Update the existing `total_time` property to roll up subtasks' time. Since nesting is single-level (a subtask can never have its own subtasks), this needs no recursion — just add each direct child's own `total_time`:

```python
@property
def total_time(self):
    own_total = (
        self.records.filter(is_complete=True).aggregate(total=Sum("duration"))["total"]
        or 0
    )
    children_total = sum(child.total_time for child in self.subtasks.all())
    return own_total + children_total
```

`total_records` is intentionally left own-only (not requested) — a parent's `total_records` still counts only its own directly-linked activity records, not its subtasks'. The serializer needs no change: `total_time` is already exposed via `serializers.IntegerField(read_only=True)` reading the model property directly, so the rollup flows through automatically once the property changes, and so does the frontend display (`formatRewardDuration(task.total_time)` in `TasksPanel.tsx`) with no changes needed there either.

### 2. Serializer (`progression/serializers.py`, `TaskSerializer`, ~line 207)

- Add `due_at`, `parent` to `Meta.fields` (read-write).
- Add `subtask_count = serializers.IntegerField(source="subtasks.count", read_only=True)` — no nested subtasks payload; the frontend already fetches the full flat list and groups client-side, so a nested payload would just be N+1 duplication.
- Add `validate()` that builds the candidate instance (falling back to `self.instance` for fields not present in a PATCH) and calls `instance.clean()`, translating `django.core.exceptions.ValidationError` into `serializers.ValidationError`. This is required because DRF doesn't call `full_clean()` automatically, and the single-level/ownership checks must run on partial updates too (e.g. a PATCH that only sends `{"parent": 5}`).

### 3. Filter (`progression/filters.py`, `TaskFilter`, ~line 93)

Add `due_at` as a `DateFromToRangeFilter`, plus `parent` (`NumberFilter` on `parent_id`) and `parent__isnull` (`BooleanFilter`, `lookup_expr="isnull"`).

### 4. ViewSet (`progression/views.py`, `TaskViewSet`)

No changes to `partial_update`'s first-completion XP-bonus logic — parent and subtask completion are fully independent, no auto-complete-parent cascade, no XP interaction. This keeps the XP logic untouched and avoids the double-fire risk of adding auto-complete semantics.

### 5. Migration

New file `progression/migrations/0006_task_due_at_parent.py`, depends on `0005_task_first_completed_at`, two `AddField` operations (see backend design notes — standard pattern matching `0005`). No DB-level CHECK constraint for the single-level rule; enforced in `clean()` only, consistent with how the rest of this model already validates.

### 6. Tests

Extend `progression/tests/test_task_models.py`: optional `due_at`, valid parent/subtask assignment, self-parent rejected, grandparent nesting rejected, parent-with-subtasts-cannot-get-a-parent rejected, cross-player parent rejected, cascade delete removes subtasks, **`total_time` on a parent equals its own completed-record duration plus the sum of its subtasks' `total_time`** (including the zero-subtasks case, to confirm the rollup doesn't change existing behavior for tasks without children).

Extend `progression/tests/test_task_api.py`: create with `due_at`, create subtask via `parent`, reject subtask-of-subtask (400), reject giving a parent to a task with existing subtasks (400, verifying the PATCH-only-`parent` case exercises the instance-fallback path), filter by `parent`/`parent__isnull`/`due_at` range, DELETE parent cascades via API, `subtask_count` accuracy in list/detail responses.

---

## Frontend

### 1. Types / API / hooks (mechanical)

- `frontend/src/types/domain.ts` — add `due_at: string | null`, `parent: number | null`, `subtask_count: number` to `Task`.
- `frontend/src/api/tasks.ts` — **fix `fetchTasks()` to page through all results** (loop on the paginated response's `next` field) instead of returning only page 1's `results`. This is a prerequisite, not optional, since subtask grouping needs the complete list.
- `useTasks.ts` — no structural changes; `Partial<Task>` payloads already pass `due_at`/`parent` through untouched on create/update.

### 2. Due-date utility (extend `frontend/src/utils/formatUtils.ts`, alongside the existing `formatRewardDuration`)

```ts
formatDueAt(dueAt: string | null): string          // display string, "-" when null
toDatetimeLocalValue(dueAt: string | null): string  // "" or "YYYY-MM-DDTHH:mm" for the input
fromDatetimeLocalValue(value: string): string | null // input value -> ISO string or null
isOverdue(dueAt: string | null, isComplete: boolean): boolean
```

### 3. Subtask grouping (`useTasksPanel.tsx`)

Add a pure derivation, run after the existing `hideCompleted`/sort logic:

```ts
interface ParentGroup { parent: ItemRecord; children: ItemRecord[] }
```

Single pass over the (already sorted) visible flat list: `Map<parentId, ItemRecord[]>` for children, top-level = tasks with `parent == null`. A task whose `parent` points to a filtered-out/missing id defensively renders as top-level (never silently drops a row). Hide-complete applies in two steps per the confirmed parent-scoped rule: drop completed top-level tasks first (removing their children with them), then independently drop completed children within each remaining group. Sort applies once to the flat list before grouping (same `compareFn`, so ordering is consistent at both levels — no separate "children always sort by X" rule to explain to users).

`useTasksPanel` exposes `groupedTasks: ParentGroup[]` (top-level list) alongside a `getChildren(task): ItemRecord[]` lookup, replacing the current flat `visibleTasks` as what `TasksPanel` passes down.

Add `due-date` to `taskSortOptions` (missing due dates sort last). Extend `getTaskMeta` with `dueAt`/`isOverdue`.

`handleCreateTask`/`handleEdit` gain an optional `parent`/`due_at` pass-through to the mutation payload (mechanical — `updateTask.mutate`/`createTask.mutate` already accept `Partial<Task>`).

### 4. Rendering — reuse `PlayerItemList` without touching `List.tsx`

Confirmed via reading `PlayerItemList.tsx`/`List.tsx`/`Li.tsx`/`usePlayerItemModal.ts` directly: `List`'s `renderItem(item)` prop already returns arbitrary JSX rendered inside one `<Li>` per top-level item — there's no need to make `List` itself nesting-aware. The plan is:

- In `PlayerItemList.tsx`, extract the existing big inline `renderItem={(item) => (...)}` block (checkbox, name, meta, row actions, hover-edit — all of it, unchanged) into a `renderRow(item: T)` helper.
- Add an optional prop `getChildren?: (item: T) => T[] | undefined`.
- The `renderItem` passed to `List` becomes: `renderRow(item)` followed by, if `getChildren(item)` is non-empty, a nested `<ul className={styles.childList}>` of `<li>` elements — reusing the `Li` component directly (imported from `../List/Li`) for each child so children get identical tone/hover/selected styling for free, each wrapping `renderRow(child)`.
- `usePlayerItemListControls`, `usePlayerItemModal`, sort/filter, and the edit/delete modal are all **untouched** — a child task clicked via its row opens the exact same modal (`handleOpenItem(child)` already works generically over any `T`), so editing/completing/deleting a subtask needs zero new modal code.
- `items` passed into `PlayerItemList` (which also feeds `usePlayerItemModal`'s live-sync lookup) should be the full flat visible list (parents + children), not just top-level — only the `List`-bound `displayItems`/`getChildren` split needs to distinguish top-level from nested for rendering purposes.
- `ProjectsPanel` (the other `PlayerItemList` consumer) simply doesn't pass `getChildren`, so it's entirely unaffected.

Styling: `styles.childList` (indent via `margin-left`) and a borderless/muted `styles.childItem` variant added to `PlayerItemList.module.scss`.

### 5. Due-date + parent editing in the modal

`renderEditSummary` (already a render-prop returning arbitrary `ReactNode` into the modal) gets extended in `TasksPanel.tsx` to include:
- A `datetime-local` input bound to `toDatetimeLocalValue(task.due_at)`, committing via `updateTask.mutate({ id: task.id, data: { due_at: fromDatetimeLocalValue(value) } })` immediately on change/blur (same "commit immediately, don't gate behind the modal's Save button" pattern already used elsewhere for the complete-checkbox) — a "Clear" button nulls it.
- A parent `<select>` populated from top-level tasks only (excluding the task being edited and any task that already has `parent != null`), disabled with an explanatory tooltip if the task being edited already has `subtask_count > 0` (pre-empting the server's 400 rather than surfacing a raw error). Commits immediately via the same `updateTask.mutate` pattern.

This avoids extending `usePlayerItemModal.ts` at all — the modal's own Save/Cancel flow stays name-only, exactly as today; due date and parent are independent immediate-commit fields rendered into the existing summary slot.

### 6. Add-subtask flow

A small row action (via the existing `renderRowActions` slot, alongside the current "start working on this task" play button) on top-level tasks only, that pre-fills/focuses `TasksPanel`'s existing add-task form with a `parent: task.id` chip shown next to the name input (clearable). One creation path — `handleCreateTask` gains the optional `parent` param threaded through to `createTask.mutate`.

### 7. Files

**Change:** `frontend/src/types/domain.ts`, `frontend/src/api/tasks.ts`, `frontend/src/utils/formatUtils.ts`, `frontend/src/components/TasksPanel/useTasksPanel.tsx`, `frontend/src/components/TasksPanel/TasksPanel.tsx`, `frontend/src/components/TasksPanel/TasksPanel.module.scss`, `frontend/src/components/PlayerItemList/PlayerItemList.tsx`, `frontend/src/components/PlayerItemList/PlayerItemList.module.scss`.

**Untouched:** `frontend/src/components/List/List.tsx`, `List/Li.tsx`, `PlayerItemList/usePlayerItemListControls.ts`, `PlayerItemList/usePlayerItemModal.ts`, `ProjectsPanel/*`.

**Tests to extend:** `frontend/src/components/TasksPanel/TasksPanel.test.tsx` (grouping/indentation, parent-scoped hide-complete, due-date input commit, add-subtask flow, parent picker exclusions), `frontend/src/components/PlayerItemList/PlayerItemList.test.tsx` (`getChildren` nested rendering, confirm `ProjectsPanel`-style usage without `getChildren` is unaffected), `frontend/src/utils/formatUtils.test.ts` (new due-date functions — create if it doesn't already exist, otherwise extend).

---

## Verification

1. Backend: `docker compose run --rm web python manage.py test progression.tests.test_task_models progression.tests.test_task_api` (prompt Duncan to run this rather than running it directly, per standing preference).
2. Frontend unit: `npm run test` (Vitest) covering the new/extended test files above.
3. Typecheck + lint: `npx tsc --noEmit` and `npm run lint`.
4. Manual/browser verification via the Browser pane against the running dev server + Docker backend (same flow used for the mode-switch work): create a task with a due date, add a subtask, confirm indentation renders, toggle "Hide complete" on a completed parent and confirm its subtasks disappear too, confirm an overdue due date renders with warning styling, confirm the parent picker excludes tasks that already have subtasks.
5. E2E: extend `frontend/tests/flows/tasks-core-loop.spec.ts` (or a new spec) with a due-date + subtask happy path once the `/tasks` heading regression from the LibraryPage refactor (tracked separately, see prior session) is resolved or worked around.
