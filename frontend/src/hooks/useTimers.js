// hooks/useTimers.js
import { useState, useRef, useEffect, useCallback } from "react";
import { apiFetch } from "../../utils/api.js";


function shuffle(array) {
  return array.sort(() => Math.random() - 0.5);
}

export default function useTimers({ mode }) {
  const [id, setId] = useState(0);
  const [status, setStatus] = useState("empty"); // "empty", "active", "waiting", "completed"
  const [duration, setDuration] = useState(0); // total seconds for timer base
  const [elapsed, setElapsed] = useState(0); // seconds elapsed (activity) or elapsed for quest
  const [subject, setSubject] = useState(null); // the current activity or quest
  const [stages, setStages] = useState([]);
  const [processedStages, setProcessedStages] = useState([]);
  const [globalStageIndex, setGlobalStageIndex] = useState(0);
  const [stageTimeRemaining, setStageTimeRemaining] = useState(
    stages[0]?.duration ?? stages[0]?.endTime ?? 0
  );

  const timerRef = useRef(null);
  const stageTimerRef = useRef(null);
  const startTimeRef = useRef(null);
  const stageStartTimeRef = useRef(null);
  const pausedTimeRef = useRef(0);

  // Timer tick handler — updates elapsed or remaining time
  const tickMain = useCallback(() => {
    if (!startTimeRef.current) return; // Safety check

    const now = Date.now();
    const secondsPassed = Math.floor((now - startTimeRef.current) / 1000);
    const newElapsed = pausedTimeRef.current + secondsPassed;

    //console.log(`[tickMain] mode: ${mode}, status: ${status}, elapsed: ${elapsed}`);

    setElapsed(newElapsed);

  }, [duration, mode]);

  const tickStage = useCallback(() => {
    const stage = stages[globalStageIndex];
    if (!stage) return;

    const now = Date.now();
    const secondsPassed = Math.floor((now - startTimeRef.current) / 1000);
    //const stageElapsed = pausedTimeRef.current + secondsPassed;

    const timeLeft = stage.duration - stageElapsed;
    setStageTimeRemaining(timeLeft);
    if (timeLeft <=0) {
      setGlobalStageIndex((prev) => prev + 1);
      //stageStartTimeRef.current = Date.now();
      pausedTimeRef.current = 0;
    }
  }, [globalStageIndex, stages]);


  // Start timer
  const start = useCallback(async () => {
    if (status === "active") return;
    if (!subject) return;
    //console.log(`[useTimers] Start ${mode}`);

    const data = await apiFetch(`/${mode}_timers/${id}/start/`, {
      method: 'POST',
    });
    setStatus("active");
    startTimeRef.current = Date.now();
    pausedTimeRef.current = elapsed;

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    timerRef.current = setInterval(() => {
      //console.log(`[START] tickMain fired for ${mode}`);
      tickMain();
    }, 1000);

    if (mode === "quest") {
      if (stageTimerRef.current) {
        clearInterval(stageTimerRef.current);
        stageTimerRef.current = null;
      }
      stageTimerRef.current = setInterval(tickStage, 1000);
    }

  }, [elapsed, status, tickMain, tickStage, subject, id]);


  // Pause timer
  const pause = useCallback(async () => {
    if (
      status === "paused" ||
      status === "waiting"
    ) return;
    if (!startTimeRef.current) return;

    //console.log(`[useTimers] Pause ${mode}`);
    const data = await apiFetch(`/${mode}_timers/${id}/pause/`, {
      method: 'POST',
    });
    const now = Date.now();
    const secondsPassed = Math.floor((now - startTimeRef.current) / 1000);
    pausedTimeRef.current += secondsPassed;

    if (mode === "activity") {
      setDuration((prev) => prev + secondsPassed);
    }

    setStatus("paused");

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (stageTimerRef.current) {
      clearInterval(stageTimerRef.current);
      stageTimerRef.current = null;
    }

    startTimeRef.current = null;

  }, [mode, status, id]);


  // Complete timer
  const complete = useCallback(async () => {
    //console.log(`[useTimers] Complete ${mode}`);
    if (status === "completed") return;

    setStatus("completed");

    const data = await apiFetch(`/${mode}_timers/${id}/complete/`, {
      method: 'POST',
    });

    //console.log(`${mode} timer complete, api data:`, data);

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (stageTimerRef.current) {
      clearInterval(stageTimerRef.current);
      stageTimerRef.current = null;
    }

  }, [mode, status]);

  // Reset timer
  const reset = useCallback(async () => {
    if (status === "empty") return;
    //console.log(`[useTimers] Reset ${mode}`);

    const data = await apiFetch(`/${mode}_timers/${id}/reset/`, {
      method: 'POST',
    });

    setStatus("empty");
    setDuration(0);
    setSubject(null);
    setElapsed(0);

    startTimeRef.current = null;
    pausedTimeRef.current = 0;

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (stageTimerRef.current) {
      clearInterval(stageTimerRef.current);
      stageTimerRef.current = null;
    }
  }, [mode, status, id]);

  // Assign subject to timer
  const assignSubject = useCallback(async (newSubject, newDuration = 0, newStatus = "waiting", newElapsed = 0) => {
    //console.log(`[useTimers] Assign ${mode}`);
    setSubject(newSubject);
    setStatus(newStatus);
    setElapsed(newElapsed);

    if (mode === "quest") {
      const data = await apiFetch(`/${mode}_timers/${id}/change_quest/`, {
        method: 'POST',
        body: JSON.stringify({ quest_id: newSubject.id, duration: newDuration }),
      });

      setDuration(newDuration);
      const quest = newSubject;
      console.log("Quest object to assign:", quest);
      let stagesEd = quest?.stages || [];
      let c = 1;
      console.log(`stagesEd v${c}:`, stagesEd);
      c++;

      // Calculate total duration of stages
      const totalStagesDuration = stagesEd.reduce((sum, stage) => {
        const dur = stage.duration ?? stage.endTime;
        return dur ? sum + dur : sum;
      }, 0);
      console.log(`Total stages duration: ${totalStagesDuration} seconds`);

      // Shuffle stages
      if (!quest.stagesFixed) {
        console.log("Quest stages are random!");
        stagesEd = shuffle([...stagesEd]);
      }
      console.log(`stagesEd v${c}:`, stagesEd);
      c++;

      // Loop stages if necessary
      if (newDuration > totalStagesDuration) {
        const numLoops = Math.ceil(newDuration / totalStagesDuration);
        stagesEd = Array(numLoops).fill().flatMap((_, loopIndex) =>
          stagesEd.map((stage, stageIndex) => ({
            stage,
            globalIndex: loopIndex * stagesEd.length + stageIndex,
          }))
        );
      } else {
        stagesEd = stagesEd.map((stage, index) => ({
          stage,
          globalIndex: index,
        }));
      }
      console.log(`stagesEd v${c}:`, stagesEd);
      c++;

      setProcessedStages(stagesEd);
      setGlobalStageIndex(0);
      console.log(`stagesEd[0]?`, stagesEd[0]);
      console.log(`Duration? ${stagesEd[0].stage.duration} ... or endTime? ${stagesEd[0].stage.endTime}`);
      setStageTimeRemaining(stagesEd[0].stage.duration ?? stagesEd[0].stage.endTime ?? 0);
      console.log('stageTimeRemaining:', stageTimeRemaining);

    } else if (mode === "activity") {
      setDuration(newDuration);
      const data = await apiFetch(`/${mode}_timers/${id}/set_activity/`, {
        method: 'POST',
        body: JSON.stringify({ activityName: newSubject }),
      });

      //console.log(`${mode} timer assign, api data:`, data);
    }
  }, [mode, id]);

  // Cleanup on unmount
  useEffect(() => {
    //console.log(`[useTimers] mounted for ${mode}`);
    return () => {
      //console.log(`[useTimers] mounted for ${mode}`);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (stageTimerRef.current) {
        clearInterval(stageTimerRef.current);
        stageTimerRef.current = null;
      }
    };
  }, []);


  const loadFromServer = useCallback((serverData) => {
    if (!serverData) return;
    //console.log("timer from server:", serverData);
    const { id, status, elapsed_time, duration, activity, quest, stages } = serverData;

    setId(id || 0);
    setStatus(status || 'empty');
    setElapsed(elapsed_time || 0);

    if (mode === 'activity' && activity) {
      setSubject(activity);
      setDuration(elapsed_time);
    }

    if (mode === 'quest' && quest) {
      setSubject(quest);
      setDuration(duration || 0);

      //console.log('quest.stages:', quest.stages);
      setStages(quest.stages || []);
    }
  }, [mode]);

  return {
    status,
    elapsed,
    remaining: mode === "quest" ? Math.max(duration - elapsed, 0) : null,
    duration,
    subject,
    processedStages,
    globalStageIndex,
    stageTimeRemaining,
    start,
    pause,
    complete,
    reset,
    assignSubject,
    loadFromServer,
  };
}
