// src/pages/TasksPage.jsx
import { useState } from "react";
import { useTasks, useCreateTask, useDeleteTask  } from "../hooks/useTasks";

import ExpandableCard from "../components/Form/Card/Card";
import Input from "../components/Input/Input";
import Button from "../components/Button/Button";
import List from "../components/List/List";


export default function TasksPage() {
  const { data: tasks, isLoading } = useTasks();
  const createTask = useCreateTask();
  const deleteTask = useDeleteTask();
  const [newName, setNewName] = useState("");

  if (isLoading) return <p>Loading tasks…</p>;

  //console.log("tasks:", tasks);

  return (
    <div>
      <h1>Tasks</h1>

      {/* Add task */}
      <form
        onSubmit={e => {
          e.preventDefault();
          if (!newName.trim()) return;
          createTask.mutate({ name: newName });
          setNewName("");
        }}
      >
        <Input
          value={newName}
          onChange={setNewName}
          placeholder="New task name"
        />
        <Button type="submit">Add task</Button>
      </form>


      <List
        items={tasks}
        renderItem={(task) => (
          <>
            <ExpandableCard
              title={task["name"]}
              children={
                <div>
                  <div>
                    Is complete: {task.is_complete.toString()}
                  </div>
                  <div>
                    Total time: {task.total_time} | Total records: {task.total_records}
                  </div>
                </div>
              }
            />

            <Button
              onClick={() => {
                if (confirm("Delete this task?")) {
                  deleteTask.mutate(task.id);
                }
              }}
            >
              Delete
            </Button>
          </>
        )}
      />
    </div>
  );
}
