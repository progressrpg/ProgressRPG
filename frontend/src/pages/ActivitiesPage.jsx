// src/pages/ActivitiesPage.jsx
import { useState } from "react";
import { useActivities, useCreateActivity, useUpdateActivity, useDeleteActivity  } from "../hooks/useActivities";

import ExpandableCard from "../components/Form/Card/Card";
import Form from "../components/Form/Form";
import Input from "../components/Input/Input";
import Button from "../components/Button/Button";
import List from "../components/List/List";


export default function ActivitiesPage() {
  const { data: activities, isLoading } = useActivities();
  const createActivity = useCreateActivity();
  const updateActivity = useUpdateActivity();
  const deleteActivity = useDeleteActivity();
  const [newName, setNewName] = useState("");
  
  if (isLoading) return <p>Loading activities…</p>;
  
  return (
    <div>
      <h1>Activities</h1>


      <List
        items={activities}
        renderItem={(activity) => (
          <>
            <ExpandableCard
              title={activity["name"]}
              children={
                <div>
                  <div>
                    Duration: {activity.duration} | Completed at: {activity.total_time}
                  </div>
                </div>
              }
            />

            <Button
              onClick={() => {
                if (confirm("Delete this activity?")) {
                  deleteActivity.mutate(activity.id);
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
