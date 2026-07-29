import React from "react";
import * as Tabs from "@radix-ui/react-tabs";

import TasksPanel from "../../components/TasksPanel/TasksPanel";
import ActivitiesPanel from "../../components/ActivitiesPanel/ActivitiesPanel";
import SkillsPanel from "../../components/SkillsPanel/SkillsPanel";
import ComingSoonPanel from "../../components/ComingSoonPanel/ComingSoonPanel";
import { useFeatureFlag } from "../../hooks/useFeatureFlag";
import styles from "./LibraryPage.module.scss";

export default function LibraryPage(): React.ReactElement {
  const hasTasksFeature = useFeatureFlag("tasksFeature");
  const hasSkillsFeature = useFeatureFlag("skillsFeature");

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Your library</h1>
      </div>

      <Tabs.Root className={styles.tabsRoot} defaultValue="activities">
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
        </Tabs.List>

        <Tabs.Content value="activities" className={styles.tabContent}>
          <ActivitiesPanel />
        </Tabs.Content>

        <Tabs.Content value="tasks" className={styles.tabContent}>
          {hasTasksFeature ? <TasksPanel /> : <ComingSoonPanel itemLabelPlural="tasks" />}
        </Tabs.Content>

        <Tabs.Content value="skills" className={styles.tabContent}>
          {hasSkillsFeature ? <SkillsPanel /> : <ComingSoonPanel itemLabelPlural="skills" />}
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
