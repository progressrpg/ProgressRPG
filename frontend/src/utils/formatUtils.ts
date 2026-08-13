export function formatDuration(duration: number): string {
  const hours = Math.floor(duration / 3600);
  const mins = Math.floor((duration % 3600) / 60);
  const secs = duration % 60;

  const paddedMins = hours > 0 ? String(mins).padStart(2, "0") : String(mins);
  const paddedSecs = String(secs).padStart(2, "0");

  return hours > 0
    ? `${hours}:${paddedMins}:${paddedSecs}`
    : `${paddedMins}:${paddedSecs}`;
}

export function formatDurationShort(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

export function pluralize(count: number, singular: string, plural: string = `${singular}s`): string {
  return count === 1 ? singular : plural;
}

export function formatRewardDuration(durationSeconds: number): string {
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

function ordinalSuffix(day: number): string {
  const remainder100 = day % 100;
  if (remainder100 >= 11 && remainder100 <= 13) return "th";
  switch (day % 10) {
    case 1:
      return "st";
    case 2:
      return "nd";
    case 3:
      return "rd";
    default:
      return "th";
  }
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

const WEEK_CUTOFF_DAYS = 56; // 8 weeks: weeks[, days] granularity applies up to this many days out/back
const MONTH_CUTOFF_DAYS = 180; // 6 months: beyond this on the future side, fall back to an absolute date

function formatWeeksAndDays(totalDays: number): string {
  const weeks = Math.floor(totalDays / 7);
  const days = totalDays % 7;
  const weeksPart = `${weeks} ${pluralize(weeks, "week")}`;
  return days > 0 ? `${weeksPart}, ${days} ${pluralize(days, "day")}` : weeksPart;
}

function formatMonths(totalDays: number): string {
  const months = Math.max(1, Math.round(totalDays / 30));
  return `${months} ${pluralize(months, "month")}`;
}

export function formatDueAt(dueAt: string | null): string {
  if (!dueAt) return "-";
  const date = new Date(dueAt);
  if (Number.isNaN(date.getTime())) return "-";

  const diffDays = Math.round(
    (startOfDay(date).getTime() - startOfDay(new Date()).getTime()) / (24 * 60 * 60 * 1000)
  );

  if (diffDays === 0) return "today";
  if (diffDays === 1) return "tomorrow";
  if (diffDays === -1) return "yesterday";

  if (diffDays > 1 && diffDays <= 6) return `in ${diffDays} days`;
  if (diffDays < -1 && diffDays >= -6) return `${-diffDays} days ago`;

  if (diffDays > 6 && diffDays <= WEEK_CUTOFF_DAYS) return `in ${formatWeeksAndDays(diffDays)}`;
  if (diffDays < -6 && diffDays >= -WEEK_CUTOFF_DAYS) return `${formatWeeksAndDays(-diffDays)} ago`;

  if (diffDays < -WEEK_CUTOFF_DAYS) return `${formatMonths(-diffDays)} ago`;

  if (diffDays > WEEK_CUTOFF_DAYS && diffDays <= MONTH_CUTOFF_DAYS) {
    return `in ${formatMonths(diffDays)}`;
  }

  // diffDays > MONTH_CUTOFF_DAYS: further out than ~6 months, show an absolute date.
  const weekday = date.toLocaleDateString(undefined, { weekday: "short" });
  const month = date.toLocaleDateString(undefined, { month: "short" });
  const day = date.getDate();
  return `${weekday} ${day}${ordinalSuffix(day)} ${month}`;
}

export function toDatetimeLocalValue(dueAt: string | null): string {
  if (!dueAt) return "";
  const date = new Date(dueAt);
  if (Number.isNaN(date.getTime())) return "";

  const pad = (n: number) => String(n).padStart(2, "0");
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());

  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

export function fromDatetimeLocalValue(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

export function isOverdue(dueAt: string | null, isComplete: boolean): boolean {
  if (!dueAt || isComplete) return false;
  const date = new Date(dueAt);
  if (Number.isNaN(date.getTime())) return false;
  return date.getTime() < Date.now();
}
