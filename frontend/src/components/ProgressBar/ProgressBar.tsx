import React, { useState } from "react";
import { Progress, View } from "tamagui";
import type { LayoutChangeEvent } from "react-native";
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

  // Measured via Tamagui's onLayout (backed by ResizeObserver on web, the
  // native layout event on RN) rather than ref.offsetWidth, so this works
  // on both platforms and re-measures on resize, not just on [percent, label]
  // changes.
  const [fillWidth, setFillWidth] = useState(0);
  const [labelWidth, setLabelWidth] = useState(0);

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
        <View
          className={styles.labelMeasure}
          aria-hidden
          onLayout={(e: LayoutChangeEvent) =>
            setLabelWidth(e.nativeEvent.layout.width)
          }
        >
          {label}
        </View>
      )}

      {label && !showInsideLabel && (
        <span className={styles.labelOutside}>{label}</span>
      )}

      <Progress
        unstyled
        className={trackClass}
        value={Math.min(value, max)}
        max={max}
        aria-label={label || `${Math.round(percent)}% complete`}
      >
        {/*
          Tamagui's Progress.Indicator has its own built-in fill behaviour:
          it renders at width 200% and slides via `x` (translateX) to reveal
          the right portion within the track's overflow:hidden clip. We
          don't want that here - ProgressBar.module.scss's plain
          width-percentage fill below is the source of truth - so `x`/
          `width` override Tamagui's internal values (props passed to a
          component always win over its own defaults) to cancel that
          behaviour out, leaving Indicator as a neutral 100%-wide wrapper.
          `height` is also set explicitly: Indicator is a flex column item
          inside the track, and being unstyled it has no height of its own,
          so without this the nested fill's `height: 100%` (below) resolves
          against an auto/content-sized parent instead of the track and the
          fill grows to fit its label text, overflowing the track's border.
        */}
        <Progress.Indicator
          unstyled
          x={0}
          width="100%"
          height="100%"
          aria-hidden={true}
        >
          <View
            className={progressClass}
            style={{ width: `${percent}%` }}
            onLayout={(e: LayoutChangeEvent) =>
              setFillWidth(e.nativeEvent.layout.width)
            }
          >
            {label && showInsideLabel && (
              <span className={styles.labelInside}>{label}</span>
            )}
          </View>
        </Progress.Indicator>
      </Progress>
    </div>
  );
};

export default ProgressBar;
