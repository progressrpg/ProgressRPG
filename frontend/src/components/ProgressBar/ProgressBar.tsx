import React, { useRef, useState, useEffect } from "react";
import { Progress } from "tamagui";
import styles from "./ProgressBar.module.scss";
import type { TimerStatus } from "../../types";

interface ProgressBarProps {
  value?: number;
  max?: number;
  label?: string;
  color?: string;
  paused?: boolean;
  status?: TimerStatus;
}

const ProgressBar = ({
  value = 0,
  max = 100,
  label,
  color = "default",
  paused = false,
}: ProgressBarProps) => {
  const percent = Math.min((value / max) * 100, 100);
  const fillRef = useRef<HTMLDivElement>(null);
  const labelMeasureRef = useRef<HTMLSpanElement>(null);

  const [fillWidth, setFillWidth] = useState(0);
  const [labelWidth, setLabelWidth] = useState(0);

  // Measure fill and label widths to decide which label to show
  useEffect(() => {
    if (fillRef.current) {
      setFillWidth(fillRef.current.offsetWidth);
    }
    if (labelMeasureRef.current) {
      setLabelWidth(labelMeasureRef.current.offsetWidth);
    }
  }, [percent, label]);

  const showInsideLabel = fillWidth > labelWidth + 10;

  const progressClass = [
    styles.progressBarFill,
    styles[color] || styles.default,
    paused ? styles.paused : "",
  ].join(" ");

  // Border-only variant of the same colour, applied to the track rather than
  // the fill class above - see the .trackDefault/etc comment in
  // ProgressBar.module.scss for why these aren't the same classes.
  const trackColorClass: Record<string, string> = {
    default: styles.trackDefault,
    warning: styles.trackWarning,
    danger: styles.trackDanger,
    success: styles.trackSuccess,
  };
  const trackClass = [
    styles.progressTrack,
    trackColorClass[color] || trackColorClass.default,
  ].join(" ");

  return (
    <div className={styles.progressBarWrapper}>
      {/* Hidden label used for measuring width */}
      {label && (
        <span
          ref={labelMeasureRef}
          className={styles.labelMeasure}
          aria-hidden
        >
          {label}
        </span>
      )}

      {label && !showInsideLabel && (
        <span className={styles.labelOutside}>{label}</span>
      )}

      <Progress
        unstyled
        className={trackClass}
        value={Math.min(value, max)}
        max={max}
        aria-label={label || undefined}
      >
        <Progress.Indicator aria-hidden="true">
          <div
            ref={fillRef}
            className={progressClass}
            style={{ width: `${percent}%` }}
          >
            {label && showInsideLabel && (
              <span className={styles.labelInside}>{label}</span>
            )}
          </div>
        </Progress.Indicator>
      </Progress>
    </div>
  );
};

export default ProgressBar;
