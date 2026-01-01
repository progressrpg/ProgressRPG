import React, { useState, useEffect } from "react";
import { useGame } from "../../context/GameContext";
import Button from "../Button/Button";
import ButtonFrame from "../Button/ButtonFrame";
import Input from "../Input/Input";
import useCombinedTimers from "../../hooks/useCombinedTimers";
import { formatDuration } from "../../../utils/formatUtils.js";
import TimerDisplay from "./TimerDisplay.jsx";
import styles from "./ActivityTimer.module.scss";

import { useTasks, useCreateTask, useUpdateTask } from "../../hooks/useTasks.js";
import { useUpdateActivity, useChangeActivityTask } from "../../hooks/useActivities.js";

export function ActivityTimer() {
  const [activityName, setActivityName] = useState('');
  const handleInputChange = (value) => {
    setActivityName(value); // record every change
  };

  const {
    onboardingStage,
    fetchActivities,
    fetchQuests,
    setPlayer,
    activityTimer,
    showToast,
  } = useGame();

  const {
    subject: activity,
    status,
    elapsed,
    assignSubject,
  } = activityTimer;

  useEffect(() => {
    if (activity && activityName === '') {
      setActivityName(activity.name);
    }
  }, [activity?.name]);

  const [selectedTask, setSelectedTask] = useState('');
  useEffect(() => {
    if (activity?.taskId != null) {
      setSelectedTask(activity.taskId.toString());
    }
  }, [activity?.taskId])

  const displayTime = formatDuration(elapsed);

  const { submitActivity, mode } = useCombinedTimers({
    enableQuest: onboardingStage >= 2,
    autoStart: onboardingStage >= 2,

    onActivityComplete: (data) => {
      if (data.profile) setPlayer(data.profile);
      fetchActivities();
    },

    onQuestComplete: (data) => {
      fetchQuests();
    },

    onError: (err) => {
      if (typeof showToast === "function") {
        showToast("Something went wrong", err);
      } else {
        console.error(err);
      }
    },
  });

  const updateActivity = useUpdateActivity();
  // const { data: tasks = [], isLoading: tasksLoading } = useTasks();
  // const updateTask = useUpdateTask();
  // const createTask = useCreateTask();
  // const changeTask = useChangeActivityTask();
  // const [creatingTask, setCreatingTask] = useState(false);
  // const [newTaskName, setNewTaskName] = useState("");

  // //console.log("tasks:", tasks);

  // const incompleteTasks = tasks.filter(task => !task.is_complete);

  console.log("act timer status:", status);

  return (
    <section className={styles.activityRow}>

      <TimerDisplay
        label="Activity"
        status={status}
        time={displayTime}
      />

      <Input
        id="activity-input"
        label="Activity"
        value={activityName}
        onChange={handleInputChange}
        placeholder="Enter activity"
      />
      {/* 🔹 Task dropdown */}
{/*
      <div className={styles.taskSelect}>
        <label htmlFor="task-select">Task</label>
        <select
          id="task-select"
          value={creatingTask ? "new" : selectedTask}
          onChange={(e) => {
            if (e.target.value === "new") {
              setCreatingTask(true);
            } else {
              setSelectedTask(e.target.value);
              setCreatingTask(false);

              if (activity?.id) {
                changeTask.mutate({ activityId: activity.id, taskId: newTaskId });
              }
            }
          }}
        >
          <option value="">
            {tasksLoading
              ? "Loading tasks..."
              : incompleteTasks.length === 0
              ? "No incomplete tasks"
              : "No task selected"}
          </option>

          {incompleteTasks.map((task) => (
            <option key={task.id} value={task.id.toString()}>
              {task.name}
            </option>
          ))}

          <option value="new">+ Create new task</option>
        </select>

        {creatingTask && (
          <div className={styles.inlineNewTask}>
            <input
              type="text"
              value={newTaskName}
              onChange={(e) => setNewTaskName(e.target.value)}
              placeholder="Enter new task name"
            />
            <button
              onClick={async () => {
                if (!newTaskName.trim()) return;
                const task = await createTask.mutateAsync({ name: newTaskName });
                setSelectedTask(task.id.toString());
                setNewTaskName("");
                setCreatingTask(false);

                if (activity?.id) {
                  changeTask.mutate({ activityId: activity.id, taskId: task.id });
                }
              }}
            >
              Add Task
            </button>
            <button onClick={() => setCreatingTask(false)}>Cancel</button>
          </div>
        )}
      </div> */}


      <ButtonFrame>
        <Button
          onClick={() => assignSubject({
            text: activityName,
            taskId: selectedTask || null,
            })
          }
          disabled={status !== "empty"}
        >
          Start Activity
        </Button>

        <Button
          onClick={async () => {
            if (activity?.id) {
              await updateActivity.mutateAsync({ activityId: activity.id, data: {name: activityName}});
            }

            await submitActivity({
              taskId: selectedTask || null,
            });

            setActivityName('');
          }}
          disabled={status === "empty"}
        >
          Submit Activity
        </Button>

{/*
        <Button
          onClick={async () => {
            if (!selectedTask) return;

            await updateTask.mutateAsync({ id: selectedTask, data: { is_complete: true } });
            setSelectedTask('');
          }}
          disabled={status !== "empty" || !selectedTask}
        >
          Complete task
        </Button> */}


      </ButtonFrame>
    </section>
  );
}
