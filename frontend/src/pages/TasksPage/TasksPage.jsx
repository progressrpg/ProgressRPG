import { useCallback, useState } from "react";

import { useTasks, useCreateTask, useUpdateTask, useDeleteTask } from "../../hooks/useTasks";
import Input from "../../components/Input/Input";
import Button from "../../components/Button/Button";
import PlayerItemList from "../../components/PlayerItemList/PlayerItemList";
import styles from "./TasksPage.module.scss";

const isTaskComplete = (task) => Boolean(task?.completed_at ?? task?.is_complete);

export default function TasksPage() {
  const { data: tasks, isLoading } = useTasks();
  const createTask = useCreateTask();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();

  const [newName, setNewName] = useState("");
  const safeTasks = Array.isArray(tasks) ? tasks : [];

  const handleCreateTask = (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    createTask.mutate({ name: newName.trim() });
    setNewName("");
  };

  const handleEdit = useCallback(
    (task, name) => {
      updateTask.mutate({ id: task.id, data: { name } });
    },
    [updateTask],
  );

  const handleDelete = useCallback(
    (task) => {
      deleteTask.mutate(task.id);
    },
    [deleteTask],
  );

  const handleToggleComplete = useCallback(
    (task) => {
      updateTask.mutate({
        id: task.id,
        data: {
          completed_at: isTaskComplete(task) ? null : new Date().toISOString(),
        },
      });
    },
    [updateTask],
  );

  if (isLoading) return <p>Loading tasks...</p>;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Tasks</h1>
      </div>

      <form className={styles.addTaskForm} onSubmit={handleCreateTask}>
        <Input
          id="new-task-name"
          value={newName}
          onChange={setNewName}
          placeholder="New task name"
          className={styles.addTaskInput}
        />
        <Button type="submit">
          <span className={styles.addButtonText}>Add task</span>
          <span className={styles.addButtonIcon} aria-hidden="true">✓</span>
        </Button>
      </form>

      {safeTasks.length > 0 ? (
        <div className={styles.tasksList}>
          <PlayerItemList
            items={safeTasks}
            itemLabel="task"
            ariaLabel="Tasks"
            isItemComplete={isTaskComplete}
            onToggleComplete={handleToggleComplete}
            renderItemMeta={(task) => (
              <>
                Total time: {task.total_time} • Records: {task.total_records}
              </>
            )}
            renderEditSummary={(task) => (
              <>
                {isTaskComplete(task) ? "Complete" : "Incomplete"} • Total time: {task.total_time}
              </>
            )}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        </div>
      ) : (
        <div className={styles.emptyState}>
          <p>No tasks yet.</p>
        </div>
      )}
    </div>
  );
}
