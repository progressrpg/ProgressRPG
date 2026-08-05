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
    paused ? styles.paused : ""
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

      {/*
        Tamagui's Progress applies its own default visuals (rounded track,
        `$background` fill, a size-driven height/width) via a styled()
        variant unless `unstyled` is set - opting out so `.progressTrack`
        stays the sole source of truth for appearance, matching how Radix's
        bare `Progress.Root` behaved. As with the Radix version, the fill is
        a plain styled `<div>` rather than Progress's own `Indicator` (which
        drives its own transform-based positioning that doesn't match this
        component's percent-width fill).
      */}
      <Progress
        unstyled
        className={styles.progressTrack}
        value={Math.min(value, max)}
        max={max}
        aria-label={label || undefined}
      >
        <div
          ref={fillRef}
          className={progressClass}
          style={{ width: `${percent}%` }}
          aria-hidden="true"
        >
          {label && showInsideLabel && (
            <span className={styles.labelInside}>{label}</span>
          )}
        </div>
      </Progress>
    </div>
  );
};

export default ProgressBar;
