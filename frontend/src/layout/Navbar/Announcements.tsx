import { useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as Accordion from "@radix-ui/react-accordion";
import Button from "../../components/Button/Button";
import styles from "./Announcements.module.scss";
import type { Announcement } from "../../types";

interface AnnouncementsData {
  announcements: Announcement[];
  unreadCount: number;
  isLoading: boolean;
  onMarkOneRead: (announcementId: number) => void;
  onMarkAllRead: () => void;
  isMarkingOneRead: boolean;
  isMarkingAllRead: boolean;
}

/** Shared header + accordion markup rendered inside both the desktop popover and the mobile panel. */
function AnnouncementsListContent({
  announcements,
  unreadCount,
  isLoading,
  onMarkOneRead,
  onMarkAllRead,
  isMarkingOneRead,
  isMarkingAllRead,
  idPrefix,
}: AnnouncementsData & { idPrefix: string }) {
  return (
    <>
      <div className={styles.header}>
        <strong>Announcements</strong>
        <button
          className={styles.actionButton}
          type="button"
          onClick={onMarkAllRead}
          disabled={unreadCount === 0 || isMarkingAllRead}
        >
          Mark all read
        </button>
      </div>

      {isLoading && <p className={styles.empty}>Loading announcements...</p>}

      {!isLoading && announcements.length === 0 && (
        <p className={styles.empty}>No announcements yet.</p>
      )}

      {!isLoading && announcements.length > 0 && (
        <Accordion.Root type="multiple" className={styles.list}>
          {announcements.map((announcement) => (
            <Accordion.Item
              key={announcement.id}
              className={styles.item}
              value={`${idPrefix}${announcement.id}`}
            >
              <Accordion.Header>
                <Accordion.Trigger className={styles.accordionTrigger}>
                  <div className={styles.titleRow}>
                    <span>{announcement.title}</span>
                    <span className={styles.metaRight}>
                      {!announcement.is_read && (
                        <span className={styles.unreadDot} aria-hidden="true" />
                      )}
                    </span>
                  </div>
                  {announcement.summary && (
                    <p className={styles.summary}>{announcement.summary}</p>
                  )}
                </Accordion.Trigger>
              </Accordion.Header>
              <Accordion.Content className={styles.accordionContent}>
                <p className={styles.body}>{announcement.body}</p>
              </Accordion.Content>
              {!announcement.is_read && (
                <button
                  className={styles.actionButton}
                  type="button"
                  onClick={() => onMarkOneRead(announcement.id)}
                  disabled={isMarkingOneRead}
                >
                  Mark read
                </button>
              )}
            </Accordion.Item>
          ))}
        </Accordion.Root>
      )}
    </>
  );
}

interface AnnouncementsBellProps extends AnnouncementsData {
  /** Navbar's shared nav-link styling, composed with this component's own trigger styling. */
  triggerClassName: string;
}

/** Desktop bell icon + unread badge that opens the announcements list in a popover. */
export function AnnouncementsBell({ triggerClassName, ...data }: AnnouncementsBellProps) {
  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <Button
          className={`${triggerClassName} ${styles.trigger}`}
          variant="secondary"
          ariaLabel="Announcements"
        >
          <span aria-hidden="true">🔔</span>
          {data.unreadCount > 0 && (
            <span className={`${styles.badge} ${styles.badgeOnTrigger}`}>
              {data.unreadCount > 99 ? "99+" : data.unreadCount}
            </span>
          )}
        </Button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className={styles.popoverContent}
          side="bottom"
          align="end"
          sideOffset={6}
        >
          <AnnouncementsListContent {...data} idPrefix="announcement-" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

interface MobileAnnouncementsProps extends AnnouncementsData {
  /** Navbar's shared dropdown-item styling. */
  itemClassName: string;
}

/** Mobile dropdown item that toggles an inline announcements panel open/closed. */
export function MobileAnnouncements({ itemClassName, ...data }: MobileAnnouncementsProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <DropdownMenu.Item
        className={itemClassName}
        onSelect={(event) => {
          event.preventDefault();
          setOpen((prev) => !prev);
        }}
      >
        <span aria-hidden="true">🔔</span>Announcements
        {data.unreadCount > 0 && (
          <span className={styles.badge}>
            {data.unreadCount > 99 ? "99+" : data.unreadCount}
          </span>
        )}
      </DropdownMenu.Item>
      {open && (
        <div className={styles.mobilePanel}>
          <AnnouncementsListContent {...data} idPrefix="mobile-announcement-" />
        </div>
      )}
    </>
  );
}
