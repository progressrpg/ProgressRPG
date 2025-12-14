import React, { useState, useEffect } from 'react';
import QuestModal from '../QuestModal/QuestModal';
import TaskSupportModal from '../TaskSupport/TaskSupport';
import GameSection from '../GameSection';
import QuestRewards from './QuestRewards';
import { useGame } from '../../../context/GameContext';
import Button from '../../../components/Button/Button';
import ButtonFrame from '../../../components/Button/ButtonFrame';
import QuestTimer from '../../../components/Timer/QuestTimer';

export default function QuestSection() {
  const { questTimer } = useGame();
  const { status, assignSubject } = questTimer;
  const [showQuestModal, setShowQuestModal] = useState(false);
  const [showTaskSupport, setShowTaskSupport] = useState(false);

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

          <Button
            className="primary"
            onClick={() => {setShowTaskSupport(true);}}
          >
            Task Support
          </Button>
        </ButtonFrame>
      )}

      {showQuestModal && (
        <QuestModal
          onClose={() => setShowQuestModal(false)}
          onChooseQuest={(quest, duration) => {
            assignSubject(quest, duration);
            setShowQuestModal(false);
          }}
        />
      )}

      {showTaskSupport && (
        <TaskSupportModal
          onClose={() => setShowTaskSupport(false)}
          onChooseQuest={(quest, duration) => {
            assignSubject(quest, duration);
            setShowTaskSupport(false);
          }}
        />
      )}

    </GameSection>
  );
}
