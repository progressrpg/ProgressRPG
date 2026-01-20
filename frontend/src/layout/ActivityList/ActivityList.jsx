import React, { useEffect, useState } from 'react';
import { apiFetch } from '../../../utils/api';
import List from '../../components/List/List';

export default function ActivityList() {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch('/player-activities/')
      .then((data) => {
        setActivities(data.results || data);
        setLoading(false);
      })
      .catch((error) => {
        console.error('Error fetching activities:', error);
        setLoading(false);
      });
  }, []);

  if (loading) return <p>Loading activities...</p>;
  if (activities.length === 0) return <p>No activities yet.</p>;

  return (
    <>
      <h2>Your Activities</h2>
      <List
        items={activities}
        renderItem={(activity) => (
          <div key={activity.id}>
            <p>{activity.name} - {new Date(activity.created_at).toLocaleString()}</p>
          </div>
        )}
      />
    </>
  );
}
