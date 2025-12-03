import React, { useState, useEffect } from 'react';
import QuestModal from '../QuestModal/QuestModal';
import GameSection from '../GameSection';
import QuestRewards from './QuestRewards';
import { useGame } from '../../../context/GameContext';
import Button from '../../../components/Button/Button';
import ButtonFrame from '../../../components/Button/ButtonFrame';
import QuestTimer from '../../../components/Timer/QuestTimer';


export default function QuestSection() {
  const { questTimer } = useGame();
  const { status, assignSubject } = questTimer;
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    if (questTimer.isComplete && status === 'active') {
      completeQuest();
    }
  }, [questTimer.isComplete, status]);

  const canChooseQuest = (status == 'completed');

  return (
    <GameSection type="Quest">
      <QuestTimer />
      <QuestRewards rewards={{ xp: 0, coins: 0 }}/>

      {canChooseQuest && (
        <ButtonFrame>
          <Button
            className="primary"
            onClick={() => {
              setModalOpen(true);
            }}
          >
            Show quests
          </Button>
        </ButtonFrame>
      )}

      {modalOpen && (
        <QuestModal
          onClose={() => setModalOpen(false)}
          onChooseQuest={(quest, duration) => {
            assignSubject(quest, duration);
            setModalOpen(false);
          }}
        />
      )}
    </GameSection>
  );
}
