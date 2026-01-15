"use client";

import { useState, useEffect, useRef } from "react";
import Modal from "../../../components/Modal/Modal";
import Button from "../../../components/Button/Button";
import ButtonFrame from "../../../components/Button/ButtonFrame";
import { useGame } from "../../../context/GameContext";


export default function TaskSupportModal({
  onClose,
  onChooseQuest,
  onStartSupport,
  onFinishSupport,
  taskSupportActive,
  lastDuration,
  setLastDuration,
}) {
  const [modalState, setModalState] = useState('welcome'); // welcome | walkthrough | suggestion | postQuest
  const [suggestion, setSuggestion] = useState();

  const { quests } = useGame();

  useEffect(() => {
    if (taskSupportActive) {
      setModalState("postQuest");
    }
  }, [taskSupportActive]);

  // Simple suggestion mapping (MVP)
  const suggestions = {
    start: "Pick the smallest possible step.",
    anxious: "Try a calming quest (breathing, stretching, or step outside).",
    tired: "Commit to 5 minutes only.",
    failure: "Do a deliberately bad version to fight perfectionism."
  };

  const backMap = {
    walkthrough: "welcome",
    suggestion: "walkthrough",
    chooseQuest: "welcome",
    postQuest: "welcome"
  };


  const quest = quests.find(quest => quest.name === "Task Support Quest"); // placeholder quest

  function startQuest(duration) {
    const chosenDuration = duration ?? lastDuration;
    setLastDuration(chosenDuration);

    if (chosenDuration == null) {
      console.warn("No duration set for quest!");
      return;
    }

    onChooseQuest?.(quest, chosenDuration);
    onStartSupport?.();
    onClose?.();
  }

  function handleWalkthroughChoice(type) {
    setSuggestion(suggestions[type]);
    setModalState("suggestion");
  }

  return (
    <>
      {modalState === "welcome" && (
        <Modal title="Welcome back!" onClose={onClose}>
          <p>How would you like to begin?</p>
          <ButtonFrame>
            <Button onClick={() => startQuest(10)}>Jump straight in</Button>
            <Button onClick={() => setModalState("walkthrough")}>
              Walkthrough
            </Button>
          </ButtonFrame>
        </Modal>
      )}

      {modalState === "walkthrough" && (
        <Modal title="What’s most difficult right now?" onClose={onClose}>
          <ButtonFrame>
            <Button onClick={() => handleWalkthroughChoice("start")}>
              Don’t know where to start
            </Button>
            <Button onClick={() => handleWalkthroughChoice("anxious")}>
              Feel anxious
            </Button>
            <Button onClick={() => handleWalkthroughChoice("tired")}>
              Too tired
            </Button>
            <Button onClick={() => handleWalkthroughChoice("failure")}>
              Fear of failure
            </Button>
          </ButtonFrame>
        </Modal>
      )}

      {modalState === "suggestion" && (
        <Modal title="Quest Suggestion" onClose={onClose}>
          <p>{suggestion}</p>
          <div>
            {[1, 3, 5].map((d) => (
              <Button key={d} onClick={() => startQuest(d*60)}>
                {d} min
              </Button>
            ))}
          </div>
          <Button
            onClick={() => setModalState(backMap[modalState])}
          >
            Back
          </Button>
        </Modal>
      )}

      {modalState === "postQuest" && (
        <Modal title="Quest complete!" onClose={onClose}>
          <p className="mt-2">Nice work. What do you need next?</p>
          <ButtonFrame>
            <Button onClick={() => startQuest(lastDuration)}>Repeat quest ({lastDuration} min)</Button>
            <Button onClick={() => setModalState("walkthrough")}>Pick another quest</Button>
            <Button onClick={() => {
              onClose?.();
              onFinishSupport?.();
              }}
            >
              Finish for now
            </Button>
          </ButtonFrame>
        </Modal>
      )}
    </>
  );
}
