import React, { useRef, useState, useEffect } from "react";
import styles from "./ProgressBar.module.scss";

const ProgressBar = ({
  value = 0,
  max = 100,
  label,
  color = "default",
  paused = false,
}) => {
  const percent = Math.min((value / max) * 100, 100);
  const fillRef = useRef(null);
  const labelMeasureRef = useRef(null);

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

      <div className={styles.progressTrack}>
        <div
          ref={fillRef}
          className={progressClass}
          style={{ width: `${percent}%` }}
        >
          {label && showInsideLabel && (
            <span className={styles.labelInside}>{label}</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProgressBar;
