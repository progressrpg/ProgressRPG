export function formatDuration(duration) {
  const hours = Math.floor(duration / 3600);
  const mins = Math.floor((duration % 3600) / 60);
  const secs = duration % 60;

  const paddedMins = hours > 0 ? String(mins).padStart(2, "0") : String(mins);
  const paddedSecs = String(secs).padStart(2, "0");

  return hours > 0
    ? `${hours}:${paddedMins}:${paddedSecs}`
    : `${paddedMins}:${paddedSecs}`;
}

export function formatRewardDuration(durationSeconds) {
  const totalSeconds = Math.max(0, Math.floor(durationSeconds));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    if (minutes > 0) {
      return `${hours} hour${hours === 1 ? "" : "s"} ${minutes} minute${minutes === 1 ? "" : "s"}`;
    }
    return `${hours} hour${hours === 1 ? "" : "s"}`;
  }

  if (minutes > 0) {
    if (seconds > 0) {
      return `${minutes} minute${minutes === 1 ? "" : "s"} ${seconds} second${seconds === 1 ? "" : "s"}`;
    }
    return `${minutes} minute${minutes === 1 ? "" : "s"}`;
  }

  return `${seconds} second${seconds === 1 ? "" : "s"}`;
}
