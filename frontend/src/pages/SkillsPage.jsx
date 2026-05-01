// src/pages/SkillsPage.jsx
import { useState } from "react";
import { useSkills, useCreateSkill, useDeleteSkill  } from "../hooks/useSkills";

import ExpandableCard from "../components/Form/Card/Card";
import Input from "../components/Input/Input";
import Button from "../components/Button/Button";
import List from "../components/List/List";


export default function SkillsPage() {
  const { data: skills, isLoading } = useSkills();
  const createSkill = useCreateSkill();
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
          <>
            <ExpandableCard
              title={skill["name"]}
              children={
                <div>
                  <div>
                    Level {skill.level}
                  </div>
                  <div>
                    Total xp: {skill.total_xp} | Total time: {skill.total_time} | Total records: {skill.total_records}
                  </div>
                </div>
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
          </>
        )}
      />
    </div>
  );
}
