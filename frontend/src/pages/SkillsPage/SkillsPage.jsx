import { useState } from "react";
import { useSkills, useCreateSkill, useUpdateSkill, useDeleteSkill } from "../../hooks/useSkills";
import Input from "../../components/Input/Input";
import Button from "../../components/Button/Button";
import styles from "./SkillsPage.module.scss";

export default function SkillsPage() {
  const { data: skills, isLoading } = useSkills();
  const createSkill = useCreateSkill();
  const updateSkill = useUpdateSkill();
  const deleteSkill = useDeleteSkill();

  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editingName, setEditingName] = useState("");

  if (isLoading) return <p>Loading skills...</p>;

  const safeSkills = Array.isArray(skills) ? skills : [];

  const handleCreateSkill = (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    createSkill.mutate({ name: newName.trim() });
    setNewName("");
  };

  const handleEditStart = (skill) => {
    setEditingId(skill.id);
    setEditingName(skill.name || "");
  };

  const handleEditCancel = () => {
    setEditingId(null);
    setEditingName("");
  };

  const handleEditSave = (skillId) => {
    if (!editingName.trim()) return;
    updateSkill.mutate({ id: skillId, data: { name: editingName.trim() } });
    handleEditCancel();
  };

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
          {safeSkills.map((skill) => (
            <div key={skill.id} className={styles.skillItem}>
              <div className={styles.skillDetails}>
                {editingId === skill.id ? (
                  <input
                    type="text"
                    className={styles.editInput}
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleEditSave(skill.id);
                      if (e.key === "Escape") handleEditCancel();
                    }}
                  />
                ) : (
                  <div className={styles.name}>{skill.name}</div>
                )}

                <div className={styles.meta}>
                  Level {skill.level} • Total XP: {skill.total_xp} • Total time: {skill.total_time} • Records: {skill.total_records}
                </div>
              </div>

              <div className={styles.actions}>
                {editingId === skill.id ? (
                  <>
                    <Button
                      className={styles.saveButton}
                      onClick={() => handleEditSave(skill.id)}
                      type="button"
                    >
                      Save
                    </Button>
                    <Button
                      variant="secondary"
                      className={styles.cancelButton}
                      onClick={handleEditCancel}
                      type="button"
                    >
                      Cancel
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      variant="secondary"
                      className={styles.editButton}
                      onClick={() => handleEditStart(skill)}
                      type="button"
                    >
                      Edit
                    </Button>
                    <Button
                      variant="danger"
                      className={styles.deleteButton}
                      onClick={() => {
                        if (confirm("Delete this skill?")) {
                          deleteSkill.mutate(skill.id);
                        }
                      }}
                      type="button"
                    >
                      Delete
                    </Button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className={styles.emptyState}>
          <p>No skills yet.</p>
        </div>
      )}
    </div>
  );
}
