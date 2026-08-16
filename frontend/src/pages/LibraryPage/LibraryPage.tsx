import React, { useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";

import TasksPanel from "../../components/TasksPanel/TasksPanel";
import ActivitiesPanel from "../../components/ActivitiesPanel/ActivitiesPanel";
import SkillsPanel from "../../components/SkillsPanel/SkillsPanel";
import NotesPanel from "../../components/NotesPanel/NotesPanel";
import ComingSoonPanel from "../../components/ComingSoonPanel/ComingSoonPanel";
import { useFeatureFlag } from "../../hooks/useFeatureFlag";
import styles from "./LibraryPage.module.scss";

export default function LibraryPage(): React.ReactElement {
  const hasTasksFeature = useFeatureFlag("tasksFeature");
  const hasSkillsFeature = useFeatureFlag("skillsFeature");
  const hasNotesFeature = useFeatureFlag("notesFeature");

  const [activeTab, setActiveTab] = useState("activities");
  const [taskToOpen, setTaskToOpen] = useState<number | null>(null);
  const [noteToOpen, setNoteToOpen] = useState<number | null>(null);

  const handleOpenTask = (taskId: number) => {
    setTaskToOpen(taskId);
    setActiveTab("tasks");
  };

  const handleOpenNote = (noteId: number) => {
    setNoteToOpen(noteId);
    setActiveTab("notes");
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Your library</h1>
      </div>

      <Tabs.Root className={styles.tabsRoot} value={activeTab} onValueChange={setActiveTab}>
        <Tabs.List className={styles.tabBar} aria-label="Your library sections">
          <Tabs.Trigger value="activities" className={styles.tab}>
            Activities
          </Tabs.Trigger>
          <Tabs.Trigger value="tasks" className={styles.tab}>
            Tasks
          </Tabs.Trigger>
          <Tabs.Trigger value="skills" className={styles.tab}>
            Skills
          </Tabs.Trigger>
          <Tabs.Trigger value="notes" className={styles.tab}>
            Notes
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="activities" className={styles.tabContent}>
          <ActivitiesPanel />
        </Tabs.Content>

        <Tabs.Content value="tasks" className={styles.tabContent}>
          {hasTasksFeature ? (
            <TasksPanel
              openTaskId={taskToOpen}
              onOpenTaskHandled={() => setTaskToOpen(null)}
              onOpenNote={handleOpenNote}
            />
          ) : (
            <ComingSoonPanel itemLabelPlural="tasks" />
          )}
        </Tabs.Content>

        <Tabs.Content value="skills" className={styles.tabContent}>
          {hasSkillsFeature ? <SkillsPanel /> : <ComingSoonPanel itemLabelPlural="skills" />}
        </Tabs.Content>

        <Tabs.Content value="notes" className={styles.tabContent}>
          {hasNotesFeature ? (
            <NotesPanel
              onOpenTask={handleOpenTask}
              openNoteId={noteToOpen}
              onOpenNoteHandled={() => setNoteToOpen(null)}
            />
          ) : (
            <ComingSoonPanel itemLabelPlural="notes" />
          )}
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
