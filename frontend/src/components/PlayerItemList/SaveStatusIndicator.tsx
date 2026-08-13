import classNames from "classnames";
import type { SaveStatus } from "./useSaveStatus";
import styles from "./PlayerItemList.module.scss";

interface SaveStatusIndicatorProps {
  status: SaveStatus;
}

const STATUS_TEXT: Record<Exclude<SaveStatus, "idle">, string> = {
  saving: "Saving…",
  saved: "Saved",
  error: "Couldn't save — try again",
};

export default function SaveStatusIndicator({ status }: SaveStatusIndicatorProps) {
  if (status === "idle") return null;

  return (
    <div
      className={classNames(styles.saveStatus, styles[`saveStatus-${status}`])}
      role={status === "error" ? "alert" : "status"}
      aria-live="polite"
    >
      {STATUS_TEXT[status]}
    </div>
  );
}
