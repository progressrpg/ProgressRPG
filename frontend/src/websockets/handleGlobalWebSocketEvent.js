// websockets/handleGlobalWebSocketEvent.js

export async function handleGlobalWebSocketEvent(data, { showToast, maintenanceRefetch, setMaintenance }) {
  switch (data.type) {
    case 'notification':
      showToast?.(data.message);
      break;
    case 'console.log':
      console.log('[WS]', data.message);
      break;
    case 'pong':
      console.log('[WS] Pong!');
      break;

    case 'action':
      switch (data.action) {

        case 'refresh':
          if (data.maintenance_active !== undefined) {
            if (data.maintenance_active) {
              setMaintenance?.({
                active: true,
                details: {
                  name: data.name,
                  description: data.description,
                  startTime: data.start_time,
                  endTime: data.end_time,
                },
              });
            } else {
              setMaintenance?.({ active: false, details: null });
            }
            return;
          }

          // Fallback: refetch from API and act on the returned value
          if (maintenanceRefetch) {
            try {
              const result = await maintenanceRefetch();
              if (result?.active) {
                setMaintenance?.(result);
              } else {
                setMaintenance?.({ active: false, details: null });
              }
            } catch (err) {
              console.warn('[WS] Error refetching maintenance status', err);
            }
          } else {
            console.warn('[WS] maintenanceRefetch not provided, cannot refresh.');
          }
          return;
          break;
        case 'load-game':
          console.log("[WS] Django consumer 'load-game' message not currently in use.");
          break;
        default:
          console.warn('[WS] Unknown action:', data);
      }
      break;

    default:
      console.warn('[WS] Unknown type:', data);
  }
}
