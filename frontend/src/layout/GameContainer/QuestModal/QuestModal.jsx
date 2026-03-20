// layout/GameContainer/QuestModal/QuestModal.jsx
import React, { useState } from 'react';
import QuestList from './QuestList/QuestList.jsx';
import QuestDetail from './QuestDetail/QuestDetail.jsx';
import { useGame } from '../../../context/GameContext.jsx';
import Button from '../../../components/Button/Button.jsx';
import Modal from '../../../components/Modal/Modal.jsx';

export default function QuestModal({ onClose, onChooseQuest }) {
  const { quests } = useGame();
  const [selectedQuest, setSelectedQuest] = useState(null);
  const [selectedDuration, setSelectedDuration] = useState(null);

  const handleViewQuest = (quest) => {
    setSelectedQuest(quest);
    setSelectedDuration(quest.duration_choices?.[0] || null);
  };

  const handleChooseQuest = () => {
    if (!selectedQuest || !selectedDuration) return;
    onChooseQuest?.(selectedQuest, selectedDuration);
    onClose();
  };

  return (
    <Modal title="Choose your quest" onClose={onClose}>
      <QuestList
        quests={quests}
        selectedQuest={selectedQuest}
        onSelect={handleViewQuest}
      />
      <QuestDetail
        quest={selectedQuest}
        selectedDuration={selectedDuration}
        onDurationChange={setSelectedDuration}
        onChoose={handleChooseQuest}
      />
    </Modal>
  );
}
