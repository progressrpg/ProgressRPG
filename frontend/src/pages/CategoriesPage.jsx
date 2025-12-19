// src/pages/CategoriesPage.jsx
import { useState } from "react";
import { useCategories, useCreateCategory, useUpdateCategory, useDeleteCategory  } from "../hooks/useCategories";

import ExpandableCard from "../components/Form/Card/Card";
import Form from "../components/Form/Form";
import Input from "../components/Input/Input";
import Button from "../components/Button/Button";
import List from "../components/List/List";


export default function CategoriesPage() {
  const { data: categories, isLoading } = useCategories();
  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();
  const deleteCategory = useDeleteCategory();
  const [newName, setNewName] = useState("");
  
  if (isLoading) return <p>Loading categories…</p>;
  
  return (
    <div>
      <h1>Categories</h1>

      {/* Add category */}
      <form
        onSubmit={e => {
          e.preventDefault();
          if (!newName.trim()) return;
          createCategory.mutate({ name: newName });
          setNewName("");
        }}
      >
        <Input
          value={newName}
          onChange={setNewName}
          placeholder="New category name"
        />
        <Button type="submit">Add category</Button>
      </form>


      <List
        items={categories}
        renderItem={(category) => (
          <>
            <ExpandableCard
              title={category["name"]}
              children={
                <div>
                  <div>
                    Level {category.level}
                  </div>
                  <div>
                    Total xp: {category.total_xp} | Total time: {category.total_time} | Total records: {category.total_records}
                  </div>
                </div>
              }
            />

            <Button
              onClick={() => {
                if (confirm("Delete this category?")) {
                  deleteCategory.mutate(category.id);
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
