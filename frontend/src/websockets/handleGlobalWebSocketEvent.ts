// websockets/handleGlobalWebSocketEvent.ts
import type { ActivityTimerApiData, IncomingWebSocketMessage } from '../types';
import type { MaintenanceState } from '../context/MaintenanceContext';

interface HandleGlobalWebSocketEventOptions {
  showToast?: (message: string) => void;
  maintenanceRefetch?: () => Promise<MaintenanceState>;
  setMaintenance?: (state: MaintenanceState) => void;
  /**
   * Called when the server pushes an authoritative activity-timer snapshot
   * (another of this player's sessions started/labelled/submitted the
   * timer) so the caller can reconcile local timer state, e.g. via
   * useActivityTimer's loadFromServer.
   */
  onActivityTimerUpdate?: (activityTimer: ActivityTimerApiData) => void;
  /**
   * Called when the server announces a newly-published Announcement, so the
   * caller can refetch the announcements list / unread-count queries.
   */
  onAnnouncementPublished?: () => void;
}

export async function handleGlobalWebSocketEvent(
  data: IncomingWebSocketMessage,
  {
    showToast,
    maintenanceRefetch,
    setMaintenance,
    onActivityTimerUpdate,
    onAnnouncementPublished,
  }: HandleGlobalWebSocketEventOptions,
): Promise<void> {
  switch (data.type) {
    case 'notification':
      showToast?.(data.message ?? '');
      break;
    case 'console.log':
      console.log('[WS]', data.message);
      break;
    case 'pong':
      console.log('[WS] Pong!');
      break;
    case 'server_message':
      break;

    case 'online_count':
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
          break;
        case 'load-game':
          console.log("[WS] Django consumer 'load-game' message not currently in use.");
          break;
        case 'activity_timer_update':
          if (data.data && 'activity_timer' in data.data) {
            onActivityTimerUpdate?.(data.data.activity_timer);
          }
          break;
        case 'announcement_published':
          onAnnouncementPublished?.();
          break;
        default:
          console.warn('[WS] Unknown action:', data);
      }
      break;

    default:
      console.warn('[WS] Unknown type:', data);
  }
}
