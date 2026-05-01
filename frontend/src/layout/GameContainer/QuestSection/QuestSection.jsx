import React, { useState } from 'react';
import QuestModal from '../QuestModal/QuestModal';
import TaskSupportModal from '../TaskSupport/TaskSupport';
import GameSection from '../GameSection';
import QuestRewards from './QuestRewards';
import { useGame } from '../../../context/GameContext';
import Button from '../../../components/Button/Button';
import ButtonFrame from '../../../components/Button/ButtonFrame';


export default function QuestSection() {
  const { questTimer } = useGame();
  const { status, assignSubject } = questTimer;
  const [showQuestModal, setShowQuestModal] = useState(false);
  const [showTaskSupport, setShowTaskSupport] = useState(false);
  const [taskSupportActive, setTaskSupportActive] = useState(false);
  const [lastTaskSupportDuration, setLastTaskSupportDuration] = useState();

  const canChooseQuest = (status === 'completed' || status === 'empty');
  const isTaskSupportOpen = showTaskSupport || (taskSupportActive && canChooseQuest);


  return (
    <GameSection type="Quest">
      <QuestRewards rewards={{ xp: 0, coins: 0 }}/>

      {canChooseQuest && (
        <ButtonFrame>
          <Button
            className="primary"
            onClick={() => {setShowQuestModal(true);}}
          >
            Show quests
          </Button>

          <Button
            className="primary"
            onClick={() => {
              setShowTaskSupport(true);
            }}
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

      {isTaskSupportOpen && (
        <TaskSupportModal
          onClose={() => {
            setShowTaskSupport(false);
            if (canChooseQuest) {
              setTaskSupportActive(false);
            }
          }}
          onChooseQuest={(quest, duration) => {
            assignSubject(quest, duration);
            setShowTaskSupport(false);
            setTaskSupportActive(true);
          }}
          taskSupportActive={taskSupportActive}
          onFinishSupport={() => {
            setTaskSupportActive(false);
          }}
          onStartSupport={() => {
            setTaskSupportActive(true);
          }}
          lastDuration={lastTaskSupportDuration}
          setLastDuration={setLastTaskSupportDuration}
        />
      )}

    </GameSection>
  );
}
