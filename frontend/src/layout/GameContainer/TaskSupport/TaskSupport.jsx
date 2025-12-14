"use client";

import { useState } from "react";
import Modal from "../../../components/Modal/Modal";
import Button from "../../../components/Button/Button";
import ButtonFrame from "../../../components/Button/ButtonFrame";

export default function TaskSupportModal() {
  const [modalState, setModalState] = useState("welcome"); // welcome | walkthrough | suggestion | postQuest | null
  const [questDuration, setQuestDuration] = useState(null);
  const [suggestion, setSuggestion] = useState(null);

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

  function startQuest(duration) {
    setQuestDuration(duration);
    setModalState(null); // close modal

  }

  function handleWalkthroughChoice(type) {
    setSuggestion(suggestions[type]);
    setModalState("suggestion");
  }

  return (
    <>
      {modalState === "welcome" && (
        <Modal title="Welcome back!" onClose={() => setModalState(null)}>
          <p>How would you like to begin?</p>
          <ButtonFrame>
            <Button onClick={() => startQuest(5)}>Jump straight in</Button>
            <Button onClick={() => setModalState("walkthrough")}>
              Walkthrough
            </Button>
          </ButtonFrame>
        </Modal>
      )}

      {modalState === "walkthrough" && (
        <Modal title="What’s most difficult right now?" onClose={() => setModalState(null)}>
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
        <Modal title="Quest Suggestion" onClose={() => setModalState(null)}>
          <p>{suggestion}</p>
          <div>
            {[5, 10, 15].map((d) => (
              <Button key={d} onClick={() => startQuest(d)}>
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
        <Modal title="Quest complete!" onClose={() => setModalState(null)}>
          <p className="mt-2">Nice work. What do you need next?</p>
          <ButtonFrame>
            <Button onClick={() => startQuest(questDuration)}>Repeat quest</Button>
            <Button onClick={() => setModalState("walkthrough")}>Pick another quest</Button>
            <Button onClick={() => setModalState(null)}>Finish for now</Button>
          </ButtonFrame>
        </Modal>
      )}
    </>
  );
}
