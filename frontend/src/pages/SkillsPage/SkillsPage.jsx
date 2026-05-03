import { useCallback, useState } from "react";

import { useSkills, useCreateSkill, useUpdateSkill, useDeleteSkill } from "../../hooks/useSkills";
import Input from "../../components/Input/Input";
import Button from "../../components/Button/Button";
import PlayerItemList from "../../components/PlayerItemList/PlayerItemList";
import styles from "./SkillsPage.module.scss";

export default function SkillsPage() {
  const { data: skills, isLoading } = useSkills();
  const createSkill = useCreateSkill();
  const updateSkill = useUpdateSkill();
  const deleteSkill = useDeleteSkill();

  const [newName, setNewName] = useState("");
  const safeSkills = Array.isArray(skills) ? skills : [];

  const handleCreateSkill = (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    createSkill.mutate({ name: newName.trim() });
    setNewName("");
  };

  const handleEdit = useCallback(
    (skill, name) => {
      updateSkill.mutate({ id: skill.id, data: { name } });
    },
    [updateSkill],
  );

  const handleDelete = useCallback(
    (skill) => {
      deleteSkill.mutate(skill.id);
    },
    [deleteSkill],
  );

  if (isLoading) return <p>Loading skills...</p>;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Skills</h1>
      </div>

      <form className={styles.addSkillForm} onSubmit={handleCreateSkill}>
        <Input
          id="new-skill-name"
          value={newName}
          onChange={setNewName}
          placeholder="New skill name"
          className={styles.addSkillInput}
        />
        <Button type="submit">Add skill</Button>
      </form>

      {safeSkills.length > 0 ? (
        <div className={styles.skillsList}>
          <PlayerItemList
            items={safeSkills}
            itemLabel="skill"
            ariaLabel="Skills"
            renderItemMeta={(skill) => (
              <>
                Level {skill.level} • Total XP: {skill.total_xp} • Total time: {skill.total_time} • Records: {skill.total_records}
              </>
            )}
            renderEditSummary={(skill) => (
              <>
                Level {skill.level} • Total XP: {skill.total_xp} • Total time: {skill.total_time} • Records: {skill.total_records}
              </>
            )}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        </div>
      ) : (
        <div className={styles.emptyState}>
          <p>No skills yet.</p>
        </div>
      )}
    </div>
  );
}
