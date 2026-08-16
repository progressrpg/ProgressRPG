// UnifiedTimerHome/TimerResultsPanel.tsx
// Results state for the unified timer (results_mode flag). Renders the
// shared RewardBreakdown plus timer-specific chrome: activity-name copy
// (live-updating if relabelled in place), task summary/complete-undo
// toggle, unlabelled inline labeling, upgrade prompt, and a manual-only
// exit — no auto-continue countdown in any case, unlike the SupportFlow
// modal's ActivityRewardScreen.
import { useEffect, useRef, useState } from "react";
import type { PlayerActivity } from "../../types";
import Button from "../Button/Button";
import ButtonFrame from "../Button/ButtonFrame";
import EntitySearchInput from "../EntitySearchInput/EntitySearchInput";
import RewardBreakdown from "../SupportFlow/screens/RewardBreakdown";
import { useTasks, useUpdateTask } from "../../hooks/useTasks";
import { useUpdateActivity } from "../../hooks/useActivities";
import { useGame } from "../../hooks/useGame";
import { formatRewardDuration } from "../../utils/formatUtils";
import type { ResultsData } from "../ActivityInput/useActivityInput";
import styles from "./TimerResultsPanel.module.scss";

const RELABEL_DEBOUNCE_MS = 1000;

interface SelectedEntity {
  name: string;
  id?: number | string | null;
  taskId?: number | null;
  source?: string;
}

function resolveSelectedTaskId(entity: SelectedEntity): number | null {
  if (entity?.source !== "task") return null;
  if (entity?.taskId !== null && entity?.taskId !== undefined) return entity.taskId;
  if (typeof entity?.id === "number") return entity.id;
  if (typeof entity?.id === "string" && /^\d+$/.test(entity.id)) return parseInt(entity.id, 10);
  return null;
}

interface TimerResultsPanelProps {
  results: ResultsData;
  onExit: () => void;
}

export default function TimerResultsPanel({ results, onExit }: TimerResultsPanelProps) {
  const { fetchPlayerAndCharacter } = useGame();
  const { data: tasks = [] } = useTasks();
  const updateTask = useUpdateTask();
  const updateActivity = useUpdateActivity();

  const [activityName, setActivityName] = useState(results.activityName);
  const [taskId, setTaskId] = useState(results.taskId);
  const [isLabeling, setIsLabeling] = useState(!results.activityName);
  const [labelDraft, setLabelDraft] = useState(results.activityName ?? "");

  const linkedTask = taskId != null ? tasks.find((t) => t.id === taskId) ?? null : null;
  const [isTaskComplete, setIsTaskComplete] = useState<boolean>(linkedTask?.is_complete ?? false);
  const hasInitialisedTaskComplete = useRef(false);
  useEffect(() => {
    if (linkedTask && !hasInitialisedTaskComplete.current) {
      setIsTaskComplete(linkedTask.is_complete);
      hasInitialisedTaskComplete.current = true;
    }
  }, [linkedTask]);

  function handleToggleTaskComplete() {
    if (!linkedTask) return;
    const next = !isTaskComplete;
    setIsTaskComplete(next);
    updateTask.mutate(
      { id: linkedTask.id, data: { is_complete: next } },
      {
        onSuccess: (data) => {
          if (data.completion_xp_gained > 0) fetchPlayerAndCharacter();
        },
      }
    );
  }

  function commitRelabel(name: string, nextTaskId: number | null) {
    if (results.activityId == null) return;
    updateActivity.mutate({
      activityId: results.activityId,
      data: { name, task_id: nextTaskId } as Partial<PlayerActivity>,
    });
    setActivityName(name || null);
    setTaskId(nextTaskId);
  }

  // Debounced live relabel: commits ~1s after the last keystroke, matching
  // the debounce pattern already used by EntitySearchInput's own search box.
  useEffect(() => {
    if (!isLabeling) return undefined;
    const trimmed = labelDraft.trim();
    if (!trimmed || trimmed === activityName) return undefined;

    const timeoutId = window.setTimeout(() => {
      commitRelabel(trimmed, taskId);
    }, RELABEL_DEBOUNCE_MS);

    return () => window.clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [labelDraft, isLabeling]);

  function handleSelectLabel(entity: SelectedEntity) {
    const resolvedTaskId = resolveSelectedTaskId(entity);
    setLabelDraft(entity.name);
    commitRelabel(entity.name, resolvedTaskId);
    setIsLabeling(false);
  }

  const summaryName = activityName || (isLabeling ? null : "an activity");

  // Duplicated (not shared) with ActivityRewardScreen's copy of this
  // calculation — used only to gate the upgrade prompt, which has
  // different surrounding chrome per host (no countdown/hover-pause here).
  const parsedTaskXpMultiplier = Number(results.taskXpMultiplier);
  const hasTaskBonus = Number.isFinite(parsedTaskXpMultiplier) && parsedTaskXpMultiplier > 1;
  const parsedMultiplier = Number(results.xpMultiplier);
  const premiumMultiplier =
    hasTaskBonus && parsedTaskXpMultiplier > 0 ? parsedMultiplier / parsedTaskXpMultiplier : parsedMultiplier;
  const isLikelyPremiumUser = premiumMultiplier >= 2;
  const shouldShowUpgradePrompt = Boolean(results.showUpgradePrompt) && !isLikelyPremiumUser;
  const upgradeMessage = shouldShowUpgradePrompt
    ? results.isAutoStopped
      ? "Need more time? Upgrade to Premium for unlimited timer sessions."
      : "Want even more rewards? Upgrade to Premium for double XP on activities."
    : null;

  return (
    <div className={styles.panel}>
      <RewardBreakdown
        activityName={summaryName}
        xpGained={results.xpGained}
        baseXp={results.baseXp}
        xpMultiplier={results.xpMultiplier}
        taskXpMultiplier={results.taskXpMultiplier}
        levelUps={results.levelUps}
        elapsedSeconds={results.elapsedSeconds}
      />

      {!activityName && results.activityId != null && (
        <div className={styles.labelPrompt}>
          {isLabeling ? (
            <EntitySearchInput
              type="activity"
              value={labelDraft}
              onChange={setLabelDraft}
              onSelect={handleSelectLabel}
              onCreate={(name) => handleSelectLabel({ name })}
              placeholder="What was this activity? e.g. washing dishes"
              ariaLabel="Label this activity"
              className={styles.labelSearch}
            />
          ) : (
            <Button variant="secondary" onClick={() => setIsLabeling(true)}>
              Label this activity
            </Button>
          )}
        </div>
      )}

      {linkedTask && (
        <div className={styles.taskCompletionPanel}>
          <p className={styles.taskCompletionTitle}>Task: {linkedTask.name}</p>
          <div className={styles.taskCompletionRow}>
            <span className={styles.taskCompletionTime}>
              Total time: {formatRewardDuration(linkedTask.total_time)}
            </span>
            <label className={styles.taskCompletionCheck}>
              Completed task?
              <input type="checkbox" checked={isTaskComplete} onChange={handleToggleTaskComplete} />
            </label>
          </div>
          {(updateTask.data?.completion_xp_gained ?? 0) > 0 && (
            <p className={styles.taskCompletionXp}>
              +{updateTask.data!.completion_xp_gained} XP for completing the task!
            </p>
          )}
        </div>
      )}

      {shouldShowUpgradePrompt && (
        <div className={styles.upgradePanel}>
          {upgradeMessage && <p>{upgradeMessage}</p>}
          <ButtonFrame>
            <Button as="a" href="/upgrade" variant="secondary">
              Upgrade to Premium
            </Button>
          </ButtonFrame>
        </div>
      )}

      <div className={styles.exitRow}>
        <ButtonFrame>
          <Button onClick={onExit}>Back to timer</Button>
        </ButtonFrame>
      </div>
    </div>
  );
}
