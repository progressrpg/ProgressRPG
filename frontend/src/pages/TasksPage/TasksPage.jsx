import { useState } from "react";
import { useTasks, useCreateTask, useUpdateTask, useDeleteTask } from "../../hooks/useTasks";
import Input from "../../components/Input/Input";
import Button from "../../components/Button/Button";
import styles from "./TasksPage.module.scss";

export default function TasksPage() {
  const { data: tasks, isLoading } = useTasks();
  const createTask = useCreateTask();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();

  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editingName, setEditingName] = useState("");

  if (isLoading) return <p>Loading tasks...</p>;

  const safeTasks = Array.isArray(tasks) ? tasks : [];

  const handleCreateTask = (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    createTask.mutate({ name: newName.trim() });
    setNewName("");
  };

  const handleEditStart = (task) => {
    setEditingId(task.id);
    setEditingName(task.name || "");
  };

  const handleEditCancel = () => {
    setEditingId(null);
    setEditingName("");
  };

  const handleEditSave = (taskId) => {
    if (!editingName.trim()) return;
    updateTask.mutate({ id: taskId, data: { name: editingName.trim() } });
    handleEditCancel();
  };

  const handleToggleComplete = (task) => {
    updateTask.mutate({
      id: task.id,
      data: { is_complete: !task.is_complete },
    });
  };

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
        <Button type="submit">Add task</Button>
      </form>

      {safeTasks.length > 0 ? (
        <div className={styles.tasksList}>
          {safeTasks.map((task) => (
            <div key={task.id} className={styles.taskItem}>
              <div className={styles.taskDetails}>
                {editingId === task.id ? (
                  <input
                    type="text"
                    className={styles.editInput}
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleEditSave(task.id);
                      if (e.key === "Escape") handleEditCancel();
                    }}
                  />
                ) : (
                  <div className={styles.name}>{task.name}</div>
                )}

                <div className={styles.meta}>
                  {task.is_complete ? "Complete" : "Incomplete"} • Total time: {task.total_time} • Records: {task.total_records}
                </div>
              </div>

              <div className={styles.actions}>
                {editingId === task.id ? (
                  <>
                    <button
                      className={styles.saveButton}
                      onClick={() => handleEditSave(task.id)}
                      type="button"
                    >
                      Save
                    </button>
                    <button
                      className={styles.cancelButton}
                      onClick={handleEditCancel}
                      type="button"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      className={styles.toggleButton}
                      onClick={() => handleToggleComplete(task)}
                      type="button"
                    >
                      {task.is_complete ? "Mark incomplete" : "Mark complete"}
                    </button>
                    <button
                      className={styles.editButton}
                      onClick={() => handleEditStart(task)}
                      type="button"
                    >
                      Edit
                    </button>
                    <button
                      className={styles.deleteButton}
                      onClick={() => {
                        if (confirm("Delete this task?")) {
                          deleteTask.mutate(task.id);
                        }
                      }}
                      type="button"
                    >
                      Delete
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className={styles.emptyState}>
          <p>No tasks yet.</p>
        </div>
      )}
    </div>
  );
}
