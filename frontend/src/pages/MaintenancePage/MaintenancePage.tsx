// pages/MaintenancePage/MaintenancePage.tsx
import React, { useEffect } from 'react';
import styles from './MaintenancePage.module.scss';
import { useMaintenanceStatus } from '../../hooks/useMaintenanceStatus';
import { useMaintenanceContext } from '../../context/MaintenanceContext';
import { useNavigate } from 'react-router';
import Button from '../../components/Button/Button';
import ButtonFrame from '../../components/Button/ButtonFrame';

export default function MaintenancePage(): React.ReactElement {
  const { active, details, refetch } = useMaintenanceStatus();
  const { maintenance, setMaintenance} = useMaintenanceContext();
  const navigate = useNavigate();

  // Optional: fetch maintenance when component mounts
  useEffect(() => {
    if (!details) refetch();
  }, [details, refetch]);

  const isActive = Boolean(active && details);
  const isFinished = !active && maintenance.justEnded;


  const handleReturnClick = () => {
    const returnTo =
    (maintenance.previousLocation && maintenance.previousLocation !== '/maintenance')
      ? maintenance.previousLocation
      : '/timer';
    // clear flags before navigating
    setMaintenance((prev) => ({ ...prev, justEnded: false, previousLocation: null }));
    navigate(returnTo, { replace: true });
  };

  if (!isActive && !isFinished) {
    return <p>No maintenance scheduled.</p>;
  }

  return (
    <div className={styles.MaintenancePage}>
      {isActive && details && (
        <>
          <h1>Site Under Maintenance</h1>
          <p>{details.name}</p>
          <p>{details.description}</p>
          <p>
            Scheduled from: {new Date(details.startTime ?? 0).toLocaleString()} <br />
            Until: {new Date(details.endTime ?? 0).toLocaleString()}
          </p>
          <p>We apologise for the inconvenience. Please check back later.</p>
        </>
      )}

      {isFinished && (
        <div className={styles.maintenanceEnded}>
          <h1>Maintenance finished!</h1>
          <p>You can now return to the app. Enjoy!</p>
          <ButtonFrame>
            <Button onClick={handleReturnClick}>Return to app</Button>
          </ButtonFrame>
        </div>
      )}
    </div>
  );
}
