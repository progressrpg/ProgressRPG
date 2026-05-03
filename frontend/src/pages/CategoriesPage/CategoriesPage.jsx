import { useState } from "react";
import { useCategories, useCreateCategory, useUpdateCategory, useDeleteCategory } from "../../hooks/useCategories";
import Input from "../../components/Input/Input";
import Button from "../../components/Button/Button";
import styles from "./CategoriesPage.module.scss";

export default function CategoriesPage() {
  const { data: categories, isLoading } = useCategories();
  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();
  const deleteCategory = useDeleteCategory();

  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editingName, setEditingName] = useState("");

  if (isLoading) return <p>Loading categories...</p>;

  const safeCategories = Array.isArray(categories) ? categories : [];

  const handleCreateCategory = (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    createCategory.mutate({ name: newName.trim() });
    setNewName("");
  };

  const handleEditStart = (category) => {
    setEditingId(category.id);
    setEditingName(category.name || "");
  };

  const handleEditCancel = () => {
    setEditingId(null);
    setEditingName("");
  };

  const handleEditSave = (categoryId) => {
    if (!editingName.trim()) return;
    updateCategory.mutate({ id: categoryId, data: { name: editingName.trim() } });
    handleEditCancel();
  };

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
          {safeCategories.map((category) => (
            <div key={category.id} className={styles.categoryItem}>
              <div className={styles.categoryDetails}>
                {editingId === category.id ? (
                  <input
                    type="text"
                    className={styles.editInput}
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleEditSave(category.id);
                      if (e.key === "Escape") handleEditCancel();
                    }}
                  />
                ) : (
                  <div className={styles.name}>{category.name}</div>
                )}

                <div className={styles.meta}>
                  Total XP: {category.total_xp} • Total time: {category.total_time} • Records: {category.total_records}
                </div>
              </div>

              <div className={styles.actions}>
                {editingId === category.id ? (
                  <>
                    <Button
                      className={styles.saveButton}
                      onClick={() => handleEditSave(category.id)}
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
                      onClick={() => handleEditStart(category)}
                      type="button"
                    >
                      Edit
                    </Button>
                    <Button
                      variant="danger"
                      className={styles.deleteButton}
                      onClick={() => {
                        if (confirm("Delete this category?")) {
                          deleteCategory.mutate(category.id);
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
          <p>No categories yet.</p>
        </div>
      )}
    </div>
  );
}
