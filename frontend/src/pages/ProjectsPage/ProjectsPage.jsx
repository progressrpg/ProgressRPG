import { useCallback, useState } from "react";

import Input from "../../components/Input/Input";
import Button from "../../components/Button/Button";
import PlayerItemList from "../../components/PlayerItemList/PlayerItemList";
import {
  useCreateProject,
  useDeleteProject,
  useProjects,
  useUpdateProject,
} from "../../hooks/useProjects";
import styles from "./ProjectsPage.module.scss";

const isProjectComplete = (project) => Boolean(project?.completed_at ?? project?.is_complete);

export default function ProjectsPage() {
  const { data: projects, isLoading } = useProjects();
  const createProject = useCreateProject();
  const updateProject = useUpdateProject();
  const deleteProject = useDeleteProject();

  const [newName, setNewName] = useState("");
  const safeProjects = Array.isArray(projects) ? projects : [];

  const handleCreateProject = (event) => {
    event.preventDefault();

    const trimmedName = newName.trim();
    if (!trimmedName) return;

    createProject.mutate({ name: trimmedName });
    setNewName("");
  };

  const handleEdit = useCallback(
    (project, name) => {
      updateProject.mutate({ id: project.id, data: { name } });
    },
    [updateProject],
  );

  const handleDelete = useCallback(
    (project) => {
      deleteProject.mutate(project.id);
    },
    [deleteProject],
  );

  const handleToggleComplete = useCallback(
    (project) => {
      updateProject.mutate({
        id: project.id,
        data: {
          completed_at: isProjectComplete(project) ? null : new Date().toISOString(),
        },
      });
    },
    [updateProject],
  );

  if (isLoading) return <p>Loading projects...</p>;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Projects</h1>
      </div>

      <form className={styles.addProjectForm} onSubmit={handleCreateProject}>
        <Input
          id="new-project-name"
          value={newName}
          onChange={setNewName}
          placeholder="New project name"
          className={styles.addProjectInput}
        />
        <Button type="submit">
          <span className={styles.addButtonText}>Add project</span>
          <span className={styles.addButtonIcon} aria-hidden="true">✓</span>
        </Button>
      </form>

      {safeProjects.length > 0 ? (
        <div className={styles.projectsList}>
          <PlayerItemList
            items={safeProjects}
            itemLabel="project"
            ariaLabel="Projects"
            isItemComplete={isProjectComplete}
            onToggleComplete={handleToggleComplete}
            renderItemMeta={(project) => (
              <>
                {project.description ? `${project.description} • ` : ""}
                Total time: {project.total_time} • Records: {project.total_records}
              </>
            )}
            renderEditSummary={(project) => (
              <>
                {isProjectComplete(project) ? "Complete" : "Incomplete"} •{" "}
                {project.description ? `${project.description} • ` : ""}
                Total time: {project.total_time} • Records: {project.total_records}
              </>
            )}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        </div>
      ) : (
        <div className={styles.emptyState}>
          <p>No projects yet.</p>
        </div>
      )}
    </div>
  );
}
