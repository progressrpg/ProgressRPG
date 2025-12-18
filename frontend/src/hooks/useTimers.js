// hooks/useTimers.js
import { useState, useRef, useEffect, useCallback } from "react";
import { apiFetch } from "../../utils/api.js";
//import { useGame } from "../context/GameContext.jsx";

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
  const [stageTimeRemaining, setStageTimeRemaining] = useState(0);

  const timerRef = useRef(null);
  const startTimeRef = useRef(null);
  const pausedTimeRef = useRef(0);

  const elapsedRef = useRef(elapsed);
  const stagesRef = useRef(stages);
  const processedStagesRef = useRef(processedStages);
  const globalStageIndexRef = useRef(globalStageIndex);

  useEffect(() => { elapsedRef.current = elapsed; }, [elapsed]);
  useEffect(() => { stagesRef.current = stages; }, [stages]);
  useEffect(() => { processedStagesRef.current = processedStages; }, [processedStages]);
  useEffect(() => { globalStageIndexRef.current = globalStageIndex; }, [globalStageIndex]);

  const stageStartTimeRef = useRef(null);
  const stageTimerRef = useRef(null);

  //const { setPlayer, setCharacter } = useGame();

  // ----------------------------
  // Tick the main quest timer
  // ----------------------------
  const tickMain = useCallback(() => {
    if (!startTimeRef.current) return;

    const now = Date.now();
    const secondsPassed = Math.floor((now - startTimeRef.current) / 1000);
    const newElapsed = pausedTimeRef.current + secondsPassed;
    setElapsed(newElapsed);
  }, []);

  // ----------------------------
  // Tick the stage timer
  // ----------------------------
  const tickStage = useCallback(() => {
    const stagesArr = processedStagesRef.current;
    let stageIdx = globalStageIndexRef.current;
    const currentStageObj = stagesArr[stageIdx];
    if (!currentStageObj) return;

    const currentStage = currentStageObj.stage;
    const stageDuration = currentStage.duration ?? currentStage.endTime ?? 0;

    // Total time consumed by all previous stages
    const previousStagesDuration = stagesArr
      .slice(0, stageIdx)
      .reduce((sum, s) => sum + (s.stage.duration ?? s.stage.endTime ?? 0), 0);

    // Stage time remaining = stage duration minus time already elapsed in this stage
    const timePassed = elapsedRef.current - previousStagesDuration;
    const timeLeft = stageDuration - timePassed;

    setStageTimeRemaining(timeLeft > 0 ? timeLeft : 0);
    if (timeLeft <= 0 && stageIdx < stagesArr.length - 1) {
      setGlobalStageIndex(stageIdx + 1);
    }
  }, []);

  // ----------------------------
  // Start timer
  // ----------------------------
  const start = useCallback(async () => {
    if (status === "active" || !subject) return;
    //console.log(`[useTimers] Start ${mode}`);

    const data = await apiFetch(`/${mode}_timers/${id}/start/`, {
      method: 'POST',
    });

    setStatus("active");
    startTimeRef.current = Date.now();
    pausedTimeRef.current = elapsedRef.current;

    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    timerRef.current = setInterval(() => {
      //console.log(`[START] tickMain fired for ${mode}`);
      tickMain();
      if (mode === "quest") tickStage();
    }, 1000);

  }, [mode, status, tickMain, tickStage, subject, id]);


  // ----------------------------
  // Pause / Complete / Reset
  // ----------------------------
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
    pausedTimeRef.current += Math.floor((now - startTimeRef.current) / 1000);
    setStatus("paused");
    //if (mode === "activity") {
    //  setDuration((prev) => prev + secondsPassed);
    //}
    if (timerRef.current) {
      clearInterval(timerRef.current);
      startTimeRef.current = null;
    }
  }, [mode, status, id]);

  const complete = useCallback(async () => {
    //console.log(`[useTimers] Complete ${mode}`);
    if (status === "completed") return;

    setStatus("completed");

    const data = await apiFetch(`/${mode}_timers/${id}/complete/`, {
      method: 'POST',
    });

    console.log(`${mode} timer complete, api data:`, data);

    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    return data;
  }, [mode, status, id]);

  const reset = useCallback(async () => {
    if (status === "empty") return;
    //console.log(`[useTimers] Reset ${mode}`);

    const data = await apiFetch(`/${mode}_timers/${id}/reset/`, {
      method: 'POST',
    });

    setStatus("empty");
    setElapsed(0);
    setDuration(0);
    setSubject(null);
    setGlobalStageIndex(0);
    setStageTimeRemaining(0);

    startTimeRef.current = null;
    pausedTimeRef.current = 0;

    if (timerRef.current) {
      clearInterval(timerRef.current);
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
      //console.log("Quest object to assign:", quest);
      let stagesEd = quest?.stages || [];
      let c = 1;
      //console.log(`stagesEd v${c}:`, stagesEd);
      c++;

      // Calculate total duration of stages
      const totalStagesDuration = stagesEd.reduce((sum, stage) => {
        const dur = stage.duration ?? stage.endTime;
        return dur ? sum + dur : sum;
      }, 0);
      //console.log(`Total stages duration: ${totalStagesDuration} seconds`);

      // Shuffle stages
      if (!quest.stages_fixed) {
        //console.log("Quest stages are random!");
        stagesEd = shuffle([...stagesEd]);
      }
      //console.log(`stagesEd v${c}:`, stagesEd);
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
      //console.log(`stagesEd v${c}:`, stagesEd);
      c++;

      setProcessedStages(stagesEd);
      setGlobalStageIndex(0);
      //console.log(`stagesEd[0]?`, stagesEd[0]);
      //console.log(`Duration? ${stagesEd[0].stage.duration} ... or endTime? ${stagesEd[0].stage.endTime}`);
      const firstStageDuration = stagesEd[0].stage.duration ?? stagesEd[0].stage.endTime ?? 0;
      const firstStageTimeLeft = firstStageDuration - newElapsed;
      setStageTimeRemaining(Math.max(firstStageTimeLeft, 0));
      //console.log('stageTimeRemaining:', newStageTime);

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
