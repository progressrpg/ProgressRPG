import { useCallback, useState } from "react";

import { useCategories, useCreateCategory, useUpdateCategory, useDeleteCategory } from "../../hooks/useCategories";
import Input from "../../components/Input/Input";
import Button from "../../components/Button/Button";
import PlayerItemList from "../../components/PlayerItemList/PlayerItemList";
import styles from "./CategoriesPage.module.scss";

export default function CategoriesPage() {
  const { data: categories, isLoading } = useCategories();
  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();
  const deleteCategory = useDeleteCategory();

  const [newName, setNewName] = useState("");
  const safeCategories = Array.isArray(categories) ? categories : [];

  const handleCreateCategory = (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    createCategory.mutate({ name: newName.trim() });
    setNewName("");
  };

  const handleEdit = useCallback(
    (category, name) => {
      updateCategory.mutate({ id: category.id, data: { name } });
    },
    [updateCategory],
  );

  const handleDelete = useCallback(
    (category) => {
      deleteCategory.mutate(category.id);
    },
    [deleteCategory],
  );

  if (isLoading) return <p>Loading categories...</p>;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Categories</h1>
      </div>

      <form className={styles.addCategoryForm} onSubmit={handleCreateCategory}>
        <Input
          id="new-category-name"
          value={newName}
          onChange={setNewName}
          placeholder="New category name"
          className={styles.addCategoryInput}
        />
        <Button type="submit">Add category</Button>
      </form>

      {safeCategories.length > 0 ? (
        <div className={styles.categoriesList}>
          <PlayerItemList
            items={safeCategories}
            itemLabel="category"
            ariaLabel="Categories"
            renderItemMeta={(category) => (
              <>
                Total XP: {category.total_xp} • Total time: {category.total_time} • Records: {category.total_records}
              </>
            )}
            renderEditSummary={(category) => (
              <>
                Total XP: {category.total_xp} • Total time: {category.total_time} • Records: {category.total_records}
              </>
            )}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        </div>
      ) : (
        <div className={styles.emptyState}>
          <p>No categories yet.</p>
        </div>
      )}
    </div>
  );
}
