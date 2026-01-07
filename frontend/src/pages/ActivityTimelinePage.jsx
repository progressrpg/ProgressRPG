import { useMemo, useEffect, useState } from "react";
import { useGame } from "../context/GameContext";
import ActivityTimeline from "../components/ActivityTimeline/ActivityTimeline";
import ActivityInput from "../components/ActivityInput/ActivityInput";

export default function ActivityTimelinePage() {

  return (
    <div>
      <h1>Activity Timeline</h1>

      <ActivityTimeline />
      <ActivityInput />

    </div>
  );
}
