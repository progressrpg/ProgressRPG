import React, { useState, useEffect } from "react";
import { useGame } from "../../context/GameContext";
import Button from "../Button/Button";
import ButtonFrame from "../Button/ButtonFrame";
import Input from "../Input/Input";
import useCombinedTimers from "../../hooks/useCombinedTimers";
import { formatDuration } from "../../../utils/formatUtils.js";
import TimerDisplay from "./TimerDisplay.jsx";
import styles from "./ActivityTimer.module.scss";

import { useSkills } from "../../hooks/useSkills.js";
import { useTasks } from "../../hooks/useTasks.js";
import { useUpdateActivity, useChangeActivitySkill, useChangeActivityTask } from "../../hooks/useActivities.js";

export function ActivityTimer() {
  const [activityName, setActivityName] = useState('');
  const handleInputChange = (value) => {
    setActivityName(value); // record every change
  };

  const { activityTimer } = useGame();
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

  const [selectedSkill, setSelectedSkill] = useState('');
  const [selectedTask, setSelectedTask] = useState('');

  useEffect(() => {
    if (activity?.taskId != null) {
      setSelectedTask(activity.taskId.toString());
    }
  }, [activity?.taskId])

  const displayTime = formatDuration(elapsed);

  const { submitActivity } = useCombinedTimers();

  const updateActivity = useUpdateActivity();

  const { data: skills = [], isLoading: skillsLoading } = useSkills();
  const changeSkill = useChangeActivitySkill();
  const { data: tasks = [], isLoading: tasksLoading } = useTasks();
  const changeTask = useChangeActivityTask();

  // console.log("Activity timer:", activityTimer);
  //console.log("activity:", activity);
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

      {/* 🔹 Skill dropdown */}
      <div className={styles.taskSelect}>
        <label htmlFor="task-select">Task</label>
        <select
          id="task-select"
          value={selectedTask}
          onChange={(e) => {
            const newTaskId = e.target.value;
            setSelectedTask(newTaskId);

            if (activity?.id) {
              changeTask.mutate({ activityId: activity.id, taskId: newTaskId });
            }
          }}
        >
          <option value="">
            {tasksLoading ? "Loading tasks..." : "No task selected"}
          </option>

          {tasks.map((task) => (
            <option key={task.id} value={task.id.toString()}>
              {task.name}
            </option>
          ))}
        </select>
      </div>

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
            setSelectedTask('');
          }}
          disabled={status === "empty"}
        >
          Submit Activity
        </Button>
      </ButtonFrame>
    </section>
  );
}
