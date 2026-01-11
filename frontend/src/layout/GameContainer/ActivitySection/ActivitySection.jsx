import React, { useState } from 'react';
import GameSection from '../GameSection';
import ActivityPanel from './ActivityPanel';
import { ActivityTimer } from '../../../components/Timer/ActivityTimer';
import { useGame } from '../../../context/GameContext.jsx';

export default function ActivitySection() {
  const { onboardingStage } = useGame();

  return (
      <GameSection type="Activity">
        <ActivityTimer />

        {onboardingStage >= 2 && (
          <ActivityPanel />
        )}
      </GameSection>
  );
}
