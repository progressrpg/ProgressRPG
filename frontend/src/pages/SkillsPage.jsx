// src/pages/SkillsPage.jsx
import { useState } from "react";
import { useSkills } from "../hooks/useSkills";
import { useCreateSkill } from "../hooks/useCreateSkill";
import { useUpdateSkill } from "../hooks/useUpdateSkill";
import { useDeleteSkill } from "../hooks/useDeleteSkill";

import Form from "../components/Form/Form";
import Input from "../components/Input/Input";
import Button from "../components/Button/Button";
import List from "../components/List/List";


export default function SkillsPage() {
  const { data: skills, isLoading } = useSkills();
  const createSkill = useCreateSkill();
  const updateSkill = useUpdateSkill();
  const deleteSkill = useDeleteSkill();

  const [newName, setNewName] = useState("");

  if (isLoading) return <p>Loading skills…</p>;

  return (
    <div>
      <h1>Skills</h1>

      {/* Add skill */}
      <form
        onSubmit={e => {
          e.preventDefault();
          if (!newName.trim()) return;
          createSkill.mutate({ name: newName });
          setNewName("");
        }}
      >
        <Input
          value={newName}
          onChange={setNewName}
          placeholder="New skill name"
        />
        <Button type="submit">Add skill</Button>
      </form>

      <List
        items={skills}
        renderItem={(skill) => (
          <div>
            <Input
              value={skill.name}
              onChange={(value) =>
                updateSkill.mutate({
                  id: skill.id,
                  data: { name: value },
                })
              }
            />

            <Button
              onClick={() => {
                if (confirm("Delete this skill?")) {
                  deleteSkill.mutate(skill.id);
                }
              }}
            >
              Delete
            </Button>
          </div>
        )}
      />
    </div>
  );
}
