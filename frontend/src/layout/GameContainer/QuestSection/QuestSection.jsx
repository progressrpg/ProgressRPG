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
  const [taskSupportActive, setTaskSupportActive] = useState(false);
  const [lastTaskSupportDuration, setLastTaskSupportDuration] = useState();


  useEffect(() => {
    if (questTimer.isComplete && status === 'active') {
      completeQuest();
    }
  }, [questTimer.isComplete, status]);

  const canChooseQuest = (status === 'completed' || status === 'empty');

  useEffect(() => {
    if (canChooseQuest && taskSupportActive) {
      setShowTaskSupport(true);
    }
  }, [canChooseQuest, taskSupportActive])


  return (
    <GameSection type="Quest">
      <QuestTimer />
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

      {showTaskSupport && (
        <TaskSupportModal
          onClose={() => setShowTaskSupport(false)}
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
